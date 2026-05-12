import math
from app.services.f5_model_module import F5ModelModule

# --- 1. MOCK DATA (Test Verileri) ---
# Gerçek projedeki dosyalarından import edilecek kısımlar
mock_team_mapping = {
    "Detroit Tigers": "DET",
    "Boston Red Sox": "BOS"
}

mock_f5_rpg = {
    "DET": {"current_2026": 2.55},
    "BOS": {"current_2026": 2.21}
}

mock_team_db = {
    "DET": {"wrc_plus": 106, "avg": 0.249},
    "BOS": {"wrc_plus": 124, "avg": 0.271}
}

mock_pitcher_metrics = {
    "Jack Flaherty": {"xera": 5.4, "siera": 5.5},
    "Sonny Gray": {"xera": 5.6, "siera": 4.4}
}

mock_bullpen = {
    "DET": 4.39, # Fallback kullanıyoruz
    "BOS": 4.39
}

# --- 2. MODELİ BAŞLATMA ---
# (F5ModelModule sınıfının yukarıda tanımlandığını varsayıyoruz)
f5_engine = F5ModelModule(
    team_name_mapping=mock_team_mapping,
    f5_rpg_database=mock_f5_rpg,
    team_database=mock_team_db,
    pitcher_metrics=mock_pitcher_metrics,
    bullpen_database=mock_bullpen
)

# --- 3. TEST ÇALIŞTIRMA ---
# Matchup: Detroit Tigers (Jack Flaherty) @ Boston Red Sox (Sonny Gray)
prediction = f5_engine.calculate(
    away_team="Detroit Tigers",
    home_team="Boston Red Sox",
    away_pitcher="Jack Flaherty",
    home_pitcher="Sonny Gray"
)

# --- 4. SONUÇLARI GÖRÜNTÜLEME ---
print("--- F5 MODEL TEST SONUÇLARI ---")
print(f"Deplasman (Tigers) Tahmini Skor: {prediction['away_score']}")
print(f"Ev Sahibi (Red Sox) Tahmini Skor: {prediction['home_score']}")
print(f"Model Toplam Sayı: {prediction['total']}")
print(f"Ev Sahibi Kazanma Olasılığı: {round(prediction['home_win_prob'] * 100, 1)}%")
print(f"Spread Avantajı: {prediction['spread_adv']}")
print("-------------------------------")