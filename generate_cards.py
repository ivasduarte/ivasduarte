import urllib.request
import sys
import json
import re
import os
import base64
import subprocess
from dataclasses import dataclass
from typing import List, Dict

# --- DOMAIN ---
@dataclass
class Stats:
    active_days: int
    streak: int
    busiest_day: str
    calendar: List[Dict]

@dataclass
class Theme:
    bg: str = "transparent"
    text: str = "#bcdae5"
    brand: str = "#9ba5f0"

# --- INFRASTRUCTURE ---
class DataRepository:
    def fetch_stats(self, filepath: str) -> Stats:
        if not os.path.exists(filepath):
            return Stats(0, 0, "N/A", [])
        
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        weeks = data.get('data', {}).get('user', {}).get('contributionsCollection', {}).get('contributionCalendar', {}).get('weeks', [])
        
        active = 0
        curr_streak = 0
        max_streak = 0
        max_count = 0
        busiest = "N/A"
        
        for w in weeks:
            for d in w['contributionDays']:
                c = d['contributionCount']
                if c > 0:
                    active += 1
                    curr_streak += 1
                    if c > max_count:
                        max_count = c
                        busiest = d['date']
                else:
                    if curr_streak > max_streak:
                        max_streak = curr_streak
                    curr_streak = 0
                    
        return Stats(active, max(max_streak, curr_streak), busiest, weeks)

class FontManager:
    def create_subset(self, font_path: str) -> str:
        # Alfabeto e números cobrem os dados dinâmicos do JSON
        chars = "0123456789-ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz:,.@|ã()&/"
        with open('chars.txt', 'w', encoding='utf-8') as f:
            f.write(chars)
            
        subprocess.run([
            sys.executable, '-m', 'fontTools.subset', font_path, 
            '--text-file=chars.txt', 
            '--flavor=woff', 
            '--output-file=subset.woff'
        ], check=True)
        
        with open('subset.woff', 'rb') as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')
            
        os.remove('chars.txt')
        os.remove('subset.woff')
        return b64

# --- APPLICATION ---
class SvgService:
    def __init__(self, theme: Theme, font_b64: str, is_static: bool):
        self.theme = theme
        self.font = font_b64
        self.is_static = is_static
        os.makedirs('cards', exist_ok=True)
        
    def _base_svg(self, width: int, height: int, delay: float, content: str) -> str:
        anim = "" if self.is_static else f"animation: fadeIn 0.8s ease {delay}s forwards;"
        opacity = "1" if self.is_static else "0"
        
        return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
<style>
@font-face {{ font-family: 'Inter'; src: url(data:font/woff;charset=utf-8;base64,{self.font}) format('woff'); }}
@keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(15px); }} to {{ opacity: 1; transform: translateY(0); }} }}
.card {{ opacity: {opacity}; {anim} }}
text {{ font-family: 'Inter', sans-serif; fill: {self.theme.text}; }}
.title {{ fill: {self.theme.brand}; font-weight: bold; font-size: 20px; }}
.sub {{ fill: {self.theme.text}; font-size: 14px; }}
@media (prefers-reduced-motion: reduce) {{
    .card {{ opacity: 1 !important; animation: none !important; transform: none !important; }}
    .smil {{ display: none; }}
}}
</style>
<g class="card">
    <rect width="100%" height="100%" rx="8" fill="{self.theme.bg}" stroke="{self.theme.brand}" stroke-opacity="0.3"/>
    {content}
</g>
</svg>"""

    def build_hero(self, delay: float):
        content = f"""
        <text x="40" y="60" class="title" font-size="28">Iva Duarte Silva</text>
        <text x="40" y="90" class="sub" font-size="16">Software Engineering Student @ ISEP | DDD, TDD &amp; Cybersecurity</text>
        """
        with open('cards/hero.svg', 'w', encoding='utf-8') as f:
            f.write(self._base_svg(800, 140, delay, content))

    def build_tile(self, name: str, title: str, subtitle: str, delay: float):
        content = f"""
        <text x="20" y="45" class="title">{title}</text>
        <text x="20" y="70" class="sub">{subtitle}</text>
        """
        with open(f'cards/tile_{name}.svg', 'w', encoding='utf-8') as f:
            f.write(self._base_svg(260, 100, delay, content))

    def build_stats(self, stats: Stats, delay: float):
        content = f"""
        <text x="40" y="50" class="title">GitHub Stats &amp; Streaks</text>
        <text x="40" y="90" class="sub">Current Streak: <tspan fill="{self.theme.brand}">{stats.streak} days</tspan></text>
        <text x="300" y="90" class="sub">Active Days: <tspan fill="{self.theme.brand}">{stats.active_days}</tspan></text>
        <text x="560" y="90" class="sub">Busiest Day: <tspan fill="{self.theme.brand}">{stats.busiest_day}</tspan></text>
        """
        with open('cards/stats.svg', 'w', encoding='utf-8') as f:
            f.write(self._base_svg(800, 140, delay, content))

    def build_repo(self, name: str, title: str, desc: str, delay: float):
        smil = f"""<circle cx="360" cy="30" r="4" fill="{self.theme.brand}">
            <animate attributeName="opacity" values="0.2;1;0.2" dur="2s" repeatCount="indefinite" class="smil"/>
        </circle>"""
        content = f"""
        <text x="20" y="40" class="title">{title}</text>
        {smil}
        <text x="20" y="75" class="sub">{desc}</text>
        """
        with open(f'cards/repo_{name}.svg', 'w', encoding='utf-8') as f:
            f.write(self._base_svg(390, 120, delay, content))

    def build_graph(self, stats: Stats, delay: float):
        boxes = []
        for i, w in enumerate(stats.calendar[-52:]):
            for d in w['contributionDays']:
                c = d['contributionCount']
                y = d['weekday'] * 15
                x = i * 15
                fill = self.theme.brand if c > 0 else "#161b22"
                op = min(1.0, 0.3 + (c * 0.15)) if c > 0 else 1.0
                boxes.append(f'<rect x="{x + 40}" y="{y + 45}" width="11" height="11" rx="2" fill="{fill}" opacity="{op}"/>')
                
        content = f"""
        <text x="40" y="25" class="title" font-size="16">Contribution Graph</text>
        {''.join(boxes)}
        """
        with open('cards/graph.svg', 'w', encoding='utf-8') as f:
            f.write(self._base_svg(800, 165, delay, content))
            
            
    def build_skills(self, delay: float):
        content = f"""
        <text x="40" y="45" class="title">Tech Stack &amp; Systems Architecture</text>
        
        <text x="40" y="80" class="sub" font-weight="bold">Languages:</text>
        <text x="135" y="80" class="sub">Java, C, Assembly (RISC-V), SQL, PL/SQL</text>
        
        <text x="40" y="105" class="sub" font-weight="bold">Architecture:</text>
        <text x="145" y="105" class="sub">Domain-Driven Design (DDD), TDD, CI/CD, Agile/Scrum</text>
        
        <text x="40" y="130" class="sub" font-weight="bold">Systems:</text>
        <text x="115" y="130" class="sub">Linux IPC (Pipes, SHM, Semaphores), TCP/UDP Sockets</text>
        
        <text x="40" y="155" class="sub" font-weight="bold">Tools &amp; DB:</text>
        <text x="135" y="155" class="sub">Oracle, Git, Maven, ANTLR, JUnit, PlantUML</text>
        """
        with open('cards/skills.svg', 'w', encoding='utf-8') as f:
            f.write(self._base_svg(800, 185, delay, content))
            
    def build_certifications(self, delay: float):
        content = f"""
        <text x="40" y="45" class="title">Complementary Certifications</text>
        
        <text x="40" y="80" class="sub" font-weight="bold">Cybersecurity:</text>
        <text x="145" y="80" class="sub">Cidadão Cibersocial &amp; Cidadão Ciberseguro (CNCS)</text>
        
        <text x="40" y="105" class="sub" font-weight="bold">Tech &amp; Mgmt:</text>
        <text x="145" y="105" class="sub">Intro to AI &amp; Digital Project Management (APD)</text>
        
        <text x="40" y="130" class="sub" font-weight="bold">Languages:</text>
        <text x="125" y="130" class="sub">EF SET English Certificate - C2 Proficient</text>
        """
        with open('cards/certs.svg', 'w', encoding='utf-8') as f:
            f.write(self._base_svg(800, 160, delay, content))

def main():
    is_static = os.environ.get('STATIC', '0') == '1'
    
    if not os.path.exists("font.ttf") or os.path.getsize("font.ttf") < 10000:
        css = urllib.request.urlopen("https://fonts.googleapis.com/css?family=Inter").read().decode('utf-8')
        
        font_url = re.search(r'url\((https://[^)]+)\)', css).group(1)
        
        urllib.request.urlretrieve(font_url, "font.ttf")
        
    theme = Theme()
    repo = DataRepository()
    stats = repo.fetch_stats('github-data.json')
    
    fm = FontManager()
    b64_font = fm.create_subset("font.ttf")
    
    svc = SvgService(theme, b64_font, is_static)
    
    svc.build_hero(delay=0.0)
    svc.build_tile('linkedin', 'LinkedIn', 'Professional Profile', delay=0.2)
    svc.build_tile('email', 'Email', 'Get in touch', delay=0.4)
    svc.build_tile('portfolio', 'Portfolio', 'Web Projects', delay=0.6)
    
    svc.build_skills(delay=0.8)
    svc.build_stats(stats, delay=1.0)
    
    svc.build_repo('aboard', 'All Aboard', 'JavaFX Railway Simulator', delay=1.3)
    svc.build_repo('logistics', 'Logistics On Rails', 'Spatial Indexes &amp; C/Assembly', delay=1.4)
    svc.build_repo('airport', 'Airport Campus', 'Cisco VLSM, OSPF &amp; Security', delay=1.5)
    svc.build_repo('aisafe', 'AISafe', 'Concurrent C Engine, IPC &amp; DDD', delay=1.6)
    svc.build_repo('portfoliocard', 'My Portfolio', 'Personal Website &amp; Projects', delay=1.7)
    svc.build_repo('adr', 'ADR API', 'Node.js API/CLI for Markdown &amp; PlantUML', delay=1.8)
    svc.build_repo('mredis', 'Mini Redis TCP', 'Node.js TCP Key-Value Store &amp; Dummy Testing', delay=1.9)
    
    svc.build_certifications(delay=1.8)
    svc.build_graph(stats, delay=2.0)

if __name__ == '__main__':
    main()