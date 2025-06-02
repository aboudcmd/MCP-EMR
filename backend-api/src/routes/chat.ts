import * as dotenv from 'dotenv';
dotenv.config();

import { Router } from 'express';
import { GroqClient } from '../groq-client';
import { MCPExecutor } from '../mcp-executor';
import { logger } from '../utils/logger';

const router = Router();
const groqClient = new GroqClient(process.env.GROQ_API_KEY!);
const mcpExecutor = new MCPExecutor(process.env.MCP_SERVER_PATH || '../mcp-server/dist/index.js');

// Define tools locally to avoid cross-project imports
const tools = [
  {
    type: 'function',
    function: {
      name: 'search_patients',
      description: 'Search for patients by name, identifier, or other criteria',
      parameters: {
        type: 'object',
        properties: {
          name: { type: 'string', description: 'Patient name to search for' },
          identifier: { type: 'string', description: 'Patient identifier' },
          birthDate: { type: 'string', description: 'Birth date (YYYY-MM-DD)' },
          gender: { type: 'string', enum: ['male', 'female', 'other'] },
        },
      },
    },
  },
  {
    type: 'function',
    function: {
      name: 'get_patient_details',
      description: 'Get detailed information about a specific patient',
      parameters: {
        type: 'object',
        properties: {
          patientId: { type: 'string', description: 'FHIR Patient resource ID' },
        },
        required: ['patientId'],
      },
    },
  },
  {
    type: 'function',
    function: {
      name: 'get_patient_conditions',
      description: 'Get all conditions/diagnoses for a patient',
      parameters: {
        type: 'object',
        properties: {
          patientId: { type: 'string', description: 'FHIR Patient resource ID' },
          clinicalStatus: {
            type: 'string',
            enum: ['active', 'recurrence', 'relapse', 'inactive', 'remission', 'resolved'],
          },
        },
        required: ['patientId'],
      },
    },
  },
  {
    type: 'function',
    function: {
      name: 'get_patient_medications',
      description: 'Get current medications for a patient',
      parameters: {
        type: 'object',
        properties: {
          patientId: { type: 'string', description: 'FHIR Patient resource ID' },
          status: { type: 'string', enum: ['active', 'completed', 'stopped'] },
        },
        required: ['patientId'],
      },
    },
  },
  {
    type: 'function',
    function: {
      name: 'get_patient_observations',
      description: 'Get observations (vitals, lab results) for a patient',
      parameters: {
        type: 'object',
        properties: {
          patientId: { type: 'string', description: 'FHIR Patient resource ID' },
          category: { type: 'string', description: 'Category of observation' },
          code: { type: 'string', description: 'LOINC code for specific observation' },
          dateFrom: { type: 'string', description: 'Start date (YYYY-MM-DD)' },
          dateTo: { type: 'string', description: 'End date (YYYY-MM-DD)' },
        },
        required: ['patientId'],
      },
    },
  },
  {
    type: 'function',
    function: {
      name: 'get_patient_encounters',
      description: 'Get encounters/visits for a patient',
      parameters: {
        type: 'object',
        properties: {
          patientId: { type: 'string', description: 'FHIR Patient resource ID' },
          type: { type: 'string', description: 'Type of encounter' },
          dateFrom: { type: 'string', description: 'Start date (YYYY-MM-DD)' },
          dateTo: { type: 'string', description: 'End date (YYYY-MM-DD)' },
        },
        required: ['patientId'],
      },
    },
  },
  {
    type: 'function',
    function: {
      name: 'get_patient_allergies',
      description: 'Get allergy and intolerance information for a patient',
      parameters: {
        type: 'object',
        properties: {
          patientId: { type: 'string', description: 'FHIR Patient resource ID' },
        },
        required: ['patientId'],
      },
    },
  },
];

const SYSTEM_PROMPT = `You are an EMR (Electronic Medical Records) assistant with access to a FHIR server through tools. You help healthcare providers query patient data, medical records, conditions, medications, and more.

Available tools:
- search_patients: Search for patients by name, identifier, birth date, or gender
- get_patient_details: Get detailed information about a specific patient
- get_patient_conditions: Get all conditions/diagnoses for a patient
- get_patient_medications: Get current medications for a patient
- get_patient_observations: Get observations (vitals, lab results) for a patient
- get_patient_encounters: Get encounters/visits for a patient
- get_patient_allergies: Get allergy information for a patient

When users ask questions:
1. Understand their intent and determine which tools to use
2. Use the appropriate tools to query the FHIR server
3. Present the information in a clear, clinically relevant format
4. Maintain patient privacy and HIPAA compliance
5. If multiple queries are needed, execute them in a logical order

Always be helpful, accurate, and provide relevant medical context when appropriate. Format responses clearly with bullet points or sections when presenting multiple pieces of information.`;

router.post('/', async (req, res) => {
  try {
    const { message, conversationHistory = [] } = req.body;

    logger.info('Received chat request', { message });

    // Format messages for Groq
    const messages = [
      ...conversationHistory,
      { role: 'user', content: message }
    ];

    // Get initial response from Groq with tools
    const initialResponse = await groqClient.chat(messages, tools, SYSTEM_PROMPT);
    
    const responseMessage = initialResponse.choices[0].message;

    // Check if Groq wants to use tools
    if (responseMessage.tool_calls && responseMessage.tool_calls.length > 0) {
      logger.info('Executing tool calls', { count: responseMessage.tool_calls.length });

      // Execute each tool call
      const toolResults = await Promise.all(
        responseMessage.tool_calls.map(async (toolCall: any) => {
          try {
            const result = await mcpExecutor.executeTool(
              toolCall.function.name,
              JSON.parse(toolCall.function.arguments)
            );

            return {
              role: 'tool',
              content: JSON.stringify(result),
              tool_call_id: toolCall.id,
            };
          } catch (error: any) {
            logger.error('Tool execution error', { tool: toolCall.function.name, error });
            return {
              role: 'tool',
              content: JSON.stringify({ error: error.message }),
              tool_call_id: toolCall.id,
            };
          }
        })
      );

      // Get final response with tool results
      const finalMessages = [
        ...messages,
        responseMessage,
        ...toolResults
      ];

      const finalResponse = await groqClient.completeWithToolResults(finalMessages, []);
      const finalMessage = finalResponse.choices[0].message;

      res.json({
        response: finalMessage.content,
        conversationHistory: [
          ...messages,
          { role: 'assistant', content: finalMessage.content }
        ],
      });
    } else {
      // No tools needed, return direct response
      res.json({
        response: responseMessage.content,
        conversationHistory: [
          ...messages,
          { role: 'assistant', content: responseMessage.content }
        ],
      });
    }
  } catch (error) {
    logger.error('Chat error', error);
    res.status(500).json({ error: 'Failed to process chat request' });
  }
});

export const chatRouter = router;