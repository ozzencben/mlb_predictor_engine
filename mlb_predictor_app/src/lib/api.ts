import axios from 'axios';
import { MLBPrediction, PredictionResponse } from '../types/mlb';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export const apiClient = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

export const getLatestPredictions = async (): Promise<MLBPrediction[]> => {
    try {
        const response = await apiClient.get<PredictionResponse>('/predictions/latest');
        return response.data.data;
    } catch (error) {
        console.error('Error fetching predictions:', error);
        throw error;
    }
};

export const triggerUpdate = async (cronSecret: string): Promise<any> => {
    try {
        const response = await apiClient.post('/cron/update', null, {
            headers: {
                'cron-secret': cronSecret,
            },
        });
        return response.data;
    } catch (error) {
        console.error('Error triggering update:', error);
        throw error;
    }
};
