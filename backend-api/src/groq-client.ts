import Groq from 'groq-sdk';
import { logger } from './utils/logger';

export class GroqClient {
  private client: Groq;

  constructor(apiKey: string) {
    this.client = new Groq({ apiKey });
  }

  async chat(messages: any[], tools: any[], systemPrompt: string) {
    try {
      const response = await this.client.chat.completions.create({
        model: 'mixtral-8x7b-32768',
        messages: [
          { role: 'system', content: systemPrompt },
          ...messages
        ],
        tools,
        tool_choice: { type: 'auto' } as any,
        temperature: 0.3,
        max_tokens: 1024,
      });

      return response;
    } catch (error) {
      logger.error('Groq API error:', error);
      throw error;
    }
  }

  async completeWithToolResults(messages: any[], toolResults: any[]) {
    try {
      const response = await this.client.chat.completions.create({
        model: 'mixtral-8x7b-32768',
        messages: [
          ...messages,
          ...toolResults
        ],
        temperature: 0.3,
        max_tokens: 1024,
      });

      return response;
    } catch (error) {
      logger.error('Groq completion error:', error);
      throw error;
    }
  }
}