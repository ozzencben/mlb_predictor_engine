import requests
from bs4 import BeautifulSoup
import time
import logging
import json
import os
from pathlib import Path
import re
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class CoversMLBScraper:
    def __init__(self):
        self.base_picks_url = "https://www.covers.com/picks/pick-count/mlb"
        self.base_matchup_url = "https://www.covers.com/sport/baseball/mlb/matchup/"
        # Covers'ın oranları çektiği gizli API
        self.base_odds_url = "https://www.covers.com/sport/hero-odds/"
        
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        }

    def clean_player_name(self, name):
        """İsimleri temizler (Örn: 'A.J. Puk' -> 'AJ Puk')."""
        if not name: return ""
        cleaned = name.replace(".", "")
        return cleaned.strip()

    def get_todays_game_ids(self):
        logging.info("Günün maç ID'leri çekiliyor...")
        try:
            response = requests.get(self.base_picks_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            game_ids = [item['gameId'] for item in data.get('gamePickCountMap', [])]
            logging.info(f"Havuzda {len(game_ids)} maç ID'si bulundu. Filtreleme başlıyor...")
            return game_ids
        except Exception as e:
            logging.error(f"Maç ID'leri alınırken hata oluştu: {e}")
            return []

    def scrape_matchup_odds(self, game_id):
        """Gizli API'den maçın Moneyline ve O/U oranlarını çeker."""
        # Varsayılan country/state parametreleriyle çağırıyoruz (Genelde bet365 veya draftkings döner)
        odds_url = f"{self.base_odds_url}{game_id}?countryCode=us&stateProvince=nv&book=default"
        
        odds_data = {
            "away_moneyline": None,
            "home_moneyline": None,
            "over_under_total": None,
            "over_odds": None,
            "under_odds": None
        }

        try:
            # Bu API genelde HTML parçası (div) döner, içindeki <span> etiketlerinden oranları çekeceğiz
            response = requests.get(odds_url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Moneyline Değerleri
                ml_container = soup.find('a', id='moneyline-book-container')
                if ml_container:
                    # ML değerleri genelde takım isimlerinin yanındaki "profit" class'lı span'lerde yazar
                    # Biz burada basitleştirilmiş bir regex veya bulucu kullanıyoruz
                    odds_text = ml_container.get_text(separator=' ').strip()
                    # Negatif veya pozitif sayıları bul (örn: -150, +130)
                    ml_matches = re.findall(r'[+-]\d+', odds_text)
                    if len(ml_matches) >= 1:
                        # İlk eşleşen genellikle favori, ikincisi sürprizdir. Ancak biz sırayı bilemiyoruz
                        # Bu yüzden bir sonraki adımda JSON API tam entegrasyonu yapacağız.
                        pass
        except Exception as e:
            logging.warning(f"Oranlar çekilirken hata: {e}")
            
        return odds_data

    def scrape_matchup_bundle(self, game_id):
        url = f"{self.base_matchup_url}{game_id}"
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # --- 0. TARİH FİLTRESİ (Gelecekteki maçları engelle) ---
            time_tag = soup.find('time')
            if time_tag and time_tag.has_attr('datetime'):
                date_str = time_tag['datetime'].split(' ')[0] # Örn: "05/12/2026"
                try:
                    game_date = datetime.strptime(date_str, "%m/%d/%Y").date()
                    today = datetime.today().date()
                    if (game_date - today).days > 1:
                        logging.warning(f"Maç ID: {game_id} gelecekte bir tarih ({date_str}). Atlanıyor!")
                        return None
                except ValueError:
                    pass

            bundle = {
                "game_id": game_id,
                "away_team": "Unknown", "home_team": "Unknown",
                "away_pitcher": None, "home_pitcher": None,
                "away_lineup": [], "home_lineup": [],
                "away_bullpen_era": 4.39, "home_bullpen_era": 4.39,
                "odds": {
                    "away_ml": None,
                    "home_ml": None,
                    "ou_total": None,
                    "over_odds": None,
                    "under_odds": None
                }
            }

            # --- 1. TAKIM İSİMLERİ (JSON-LD ile Kusursuz Tespit) ---
            json_script = soup.find('script', type='application/ld+json')
            if json_script:
                try:
                    data = json.loads(json_script.string)
                    bundle["away_team"] = data.get('awayTeam', {}).get('name', "Unknown")
                    bundle["home_team"] = data.get('homeTeam', {}).get('name', "Unknown")
                except: pass

            # Fallback (Eğer JSON-LD yoksa eski yöntemle kurtar)
            if bundle["away_team"] == "Unknown":
                away_img = soup.select_one('.away-team .matchupteam-logo')
                if away_img and 'alt' in away_img.attrs: bundle["away_team"] = away_img['alt'].replace(' logo', '').strip()

            if bundle["home_team"] == "Unknown":
                home_img = soup.select_one('.home-team .matchupteam-logo')
                if home_img and 'alt' in home_img.attrs: bundle["home_team"] = home_img['alt'].replace(' logo', '').strip()

            logging.info(f"Maç Kazınıyor: {bundle['away_team']} @ {bundle['home_team']} (ID: {game_id})")

            # --- 1.5 ORANLARI ÇEKME (Senin Bulduğun Projection-Body Yöntemi) ---
            # Sayfa içinde "fetchProjectionBody" veya "adjustBarWidths" fonksiyonunu arıyoruz
            script_tags = soup.find_all('script')
            for script in script_tags:
                if script.string and "fetchProjectionBody" in script.string:
                    # URL'yi Regex ile yakala: /sport/baseball/mlb/matchup/369587/projection-body/4.16/4.17
                    match = re.search(r'(/sport/baseball/mlb/matchup/\d+/projection-body/[0-9.]+/[0-9.]+)', script.string)
                    if match:
                        projection_url = f"https://www.covers.com{match.group(1)}?countryCode=us&stateProvince=nv&isOnMobile=false"
                        try:
                            proj_resp = requests.get(projection_url, headers=self.headers, timeout=10)
                            if proj_resp.status_code == 200:
                                proj_data = proj_resp.json()
                                # JSON İçinden Pırlanta Gibi Oranları Çek
                                bundle["odds"]["ou_total"] = proj_data.get("oddsTotal")
                                bundle["odds"]["over_odds"] = proj_data.get("overOdds")
                                bundle["odds"]["under_odds"] = proj_data.get("underOdds")
                                
                                # Moneyline
                                best_ml = proj_data.get("bestMoneyLine")
                                ml_data = best_ml.get("sides", []) if best_ml else []
                                for side in ml_data:
                                    if side.get("sideLabel") == "Away":
                                        bundle["odds"]["away_ml"] = side.get("americanOdds")
                                    elif side.get("sideLabel") == "Home":
                                        bundle["odds"]["home_ml"] = side.get("americanOdds")
                        except Exception as e:
                            logging.warning(f"Oran API Hatası (ID: {game_id}): {e}")
                    break

            # --- 2. STARTING PITCHERS (Çok Katmanlı Zırh) ---
            for prefix in ["away", "home"]:
                starter_section = soup.find('div', id=f'{prefix}-team-last-5')
                if starter_section:
                    h3 = starter_section.find('h3', class_='starter-with-teamLogo')
                    if h3 and "TBD" not in h3.text.upper():
                        a_tag = h3.find('a', class_='anchor-with-border')
                        raw_name = a_tag.text if a_tag else h3.text.replace("Last 5", "").replace("starter", "").strip()
                        bundle[f"{prefix}_pitcher"] = self.clean_player_name(raw_name.split('(')[0])

            if not bundle["away_pitcher"] or not bundle["home_pitcher"]:
                pitchers_box = soup.find('div', id='pitchers')
                if pitchers_box:
                    for prefix in ["away", "home"]:
                        if not bundle[f"{prefix}_pitcher"]:
                            p_tag = pitchers_box.find('p', {'aria-labelledby': f'{prefix}-pitcher'})
                            if p_tag and p_tag.find('a'):
                                bundle[f"{prefix}_pitcher"] = self.clean_player_name(p_tag.find('a').text.split('(')[0])

            # --- 3. STARTING LINEUPS ---
            lineup_tables = soup.select('table.cmg_team_lineup, .cmg_matchup_lineup_table')
            if len(lineup_tables) >= 2:
                for i, key in enumerate(["away_lineup", "home_lineup"]):
                    for row in lineup_tables[i].find_all('tr')[1:10]: 
                        if row.find('td'):
                            raw_name = row.find('td').text.strip()
                            clean_name = re.sub(r'^\d+\.\s*', '', raw_name).split(',')[0].strip()
                            if len(clean_name) > 3: bundle[key].append(self.clean_player_name(clean_name))

            for prefix, title in [("away", "BoxscoreBatterAway"), ("home", "BoxscoreBatterHome")]:
                if not bundle[f"{prefix}_lineup"]:
                    batting_tab = soup.find('div', id=title)
                    if batting_tab:
                        for row in batting_tab.select('tbody tr')[:9]: 
                            if row.find('a'): bundle[f"{prefix}_lineup"].append(self.clean_player_name(row.find('a').text.strip()))

            # --- 4. BULLPEN (DİNAMİK HESAPLAMA) ---
            tables = soup.find_all('table')
            bullpen_tables_found = 0
            for table in tables:
                headers = [th.text.strip().upper() for th in table.find_all('th')]
                if not headers: continue
                
                if "BULLPEN" in headers[0]:
                    bullpen_tables_found += 1
                    try:
                        ip_idx = headers.index("IP")
                        er_idx = headers.index("ER")
                    except ValueError: continue 
                        
                    total_ip, total_er = 0.0, 0
                    for row in table.find_all('tr')[1:]:
                        cols = row.find_all('td')
                        if len(cols) > max(ip_idx, er_idx):
                            p_name = cols[0].text.strip().lower()
                            if "last 3" in p_name or "total" in p_name or "available" in p_name or not p_name: 
                                continue
                                
                            try:
                                ip_parts = cols[ip_idx].text.strip().split('.')
                                val = float(ip_parts[0])
                                if len(ip_parts) > 1:
                                    if ip_parts[1] == '1': val += 0.333
                                    elif ip_parts[1] == '2': val += 0.666
                                total_ip += val
                                total_er += int(cols[er_idx].text.strip())
                            except ValueError: continue
                    
                    if total_ip > 0:
                        era = round((total_er / total_ip) * 9, 2)
                        if bullpen_tables_found == 1: bundle["away_bullpen_era"] = era
                        elif bullpen_tables_found == 2: bundle["home_bullpen_era"] = era

            return bundle
        except Exception as e:
            logging.error(f"Error in {game_id}: {e}")
            return None

    def build_and_save_daily_db(self, filename="data/daily_matchups.json"):
        game_ids = self.get_todays_game_ids()
        daily_matches = []

        for game_id in game_ids:
            bundle = self.scrape_matchup_bundle(game_id)
            if bundle:
                daily_matches.append(bundle)
            time.sleep(2) 

        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(daily_matches, f, indent=4, ensure_ascii=False)
            
        logging.info(f"Günün Tüm Maç Verileri başarıyla '{filename}' dosyasına kaydedildi!")
        return daily_matches

if __name__ == "__main__":
    scraper = CoversMLBScraper()
    guncel_veriler = scraper.build_and_save_daily_db()
    
    print("\n--- ÇEKİLEN MAÇ ÖRNEĞİ ---")
    if guncel_veriler:
        ornek_mac = guncel_veriler[0]
        print(f"Maç: {ornek_mac['away_team']} vs {ornek_mac['home_team']}")
        print(f"Atıcılar: {ornek_mac['away_pitcher']} vs {ornek_mac['home_pitcher']}")
        print(f"Deplasman Bullpen: {ornek_mac['away_bullpen_era']} | Ev Sahibi Bullpen: {ornek_mac['home_bullpen_era']}")
        print(f"Bahis Oranları:")
        print(f"  Away ML: {ornek_mac['odds']['away_ml']} | Home ML: {ornek_mac['odds']['home_ml']}")
        print(f"  O/U Total: {ornek_mac['odds']['ou_total']} (Over: {ornek_mac['odds']['over_odds']}, Under: {ornek_mac['odds']['under_odds']})")