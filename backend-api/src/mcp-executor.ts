import { spawn } from 'child_process';
import { logger } from './utils/logger';

export class MCPExecutor {
  private mcpServerPath: string;

  constructor(mcpServerPath: string) {
    this.mcpServerPath = mcpServerPath;
  }

  async executeTool(toolName: string, args: any): Promise<any> {
    return new Promise((resolve, reject) => {
      const mcpProcess = spawn('node', [this.mcpServerPath], {
        stdio: ['pipe', 'pipe', 'pipe'],
      });

      let output = '';
      let error = '';

      // Send tool request
      const request = {
        jsonrpc: '2.0',
        method: 'tools/call',
        params: {
          name: toolName,
          arguments: args,
        },
        id: 1,
      };

      mcpProcess.stdin.write(JSON.stringify(request) + '\n');

      mcpProcess.stdout.on('data', (data) => {
        output += data.toString();
      });

      mcpProcess.stderr.on('data', (data) => {
        error += data.toString();
      });

      mcpProcess.on('close', (code) => {
        if (code !== 0) {
          reject(new Error(`MCP process exited with code ${code}: ${error}`));
        } else {
          try {
            const response = JSON.parse(output);
            resolve(response.result);
          } catch (e) {
            reject(new Error(`Failed to parse MCP response: ${output}`));
          }
        }
      });

      mcpProcess.on('error', (err) => {
        reject(err);
      });
    });
  }
}