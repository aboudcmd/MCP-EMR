// backend-api/src/groq-client.ts

import Groq from 'groq-sdk';
import { logger } from './utils/logger';

export class GroqClient {
  private client: Groq;

  constructor(apiKey: string) {
    this.client = new Groq({ apiKey });
  }

  async chat(messages: any[], tools: any[], systemPrompt: string) {
    try {
      // Build the payload as a plain object (with snake_case tool_choice)
      const payload = {
        model: 'llama-3.3-70b-versatile',
        messages: [
          { role: 'system', content: systemPrompt },
          ...messages,
        ],
        tools,                 // array of your function schemas
        tool_choice: 'auto',   // <-- snake_case here
        temperature: 0.3,
        max_tokens: 1024,
      };

      // Cast to any so TypeScript does not complain about 'tool_choice'
      const response = await this.client.chat.completions.create(
        payload as any
      );

      return response;
    } catch (error) {
      logger.error('Groq API error:', error);
      throw error;
    }
  }

  async completeWithToolResults(messages: any[], toolResults: any[]) {
    try {
      const payload = {
        model: 'llama-3.3-70b-versatile',
        messages: [
          ...messages,
          ...toolResults,
        ],
        temperature: 0.3,
        max_tokens: 1024,
      };

      const response = await this.client.chat.completions.create(
        payload as any
      );

      return response;
    } catch (error) {
      logger.error('Groq completion error:', error);
      throw error;
    }
  }
}
