export interface Edge {
    value: string;
    edge_pct: number;
}

export interface MLBPrediction {
    matchup: string;
    pitchers: string;
    nrfi_prob: number;
    f5_pick: string;
    ou_play: string;
    ou_edge: number;
    ml_value: string;
    ml_edge: number;
    raw_prediction?: any;
    raw_odds?: any;
}

export interface PredictionResponse {
    status: string;
    data: MLBPrediction[];
}
