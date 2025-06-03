import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import dotenv from 'dotenv';
import { chatRouter } from './routes/chat';
import { errorHandler } from './middleware/error-handler';
import { logger } from './utils/logger';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(helmet());
app.use(cors({
  origin: process.env.CORS_ORIGIN || 'http://localhost:3000',
  credentials: true,  // Add this for cookie support if needed
}));
app.use(express.json());

// Health check
app.get('/health', (req: express.Request, res: express.Response) => {
  res.json({ 
    status: 'ok', 
    timestamp: new Date().toISOString(),
    services: {
      backend: 'running',
      port: PORT
    }
  });
});

// Routes
app.use('/api/chat', chatRouter);

// Error handling
app.use(errorHandler);

app.listen(PORT, () => {
  logger.info(`Backend API running on port ${PORT}`);
  logger.info(`CORS enabled for: ${process.env.CORS_ORIGIN || 'http://localhost:3000'}`);
});