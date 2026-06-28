from pathlib import Path
import pandas as pd
import numpy as np

BASE = Path(__file__).resolve().parents[1]
RAW = BASE/'data'/'raw'
OUT = BASE/'data'/'processed'
FIG = BASE/'outputs'/'figures'
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

START, END = 2022, 2025
ALCARAZ = 'Carlos Alcaraz'

def read_csv(name):
    return pd.read_csv(RAW/name, low_memory=False)

def add_match_meta(df, matches):
    cols = ['match_id','date','year','Tournament','Round','Surface','Player 1','Player 2','p1_winner']
    return df.merge(matches[cols], on='match_id', how='inner')

matches = read_csv('charting-m-matches.csv')
matches['date'] = pd.to_datetime(matches['Date'].astype(str), format='%Y%m%d', errors='coerce')
matches['year'] = matches['date'].dt.year
matches = matches[(matches['year']>=START)&(matches['year']<=END)].copy()
# In Tennis Charting match_id order usually is the winner of match  for ATP files
matches['p1_winner'] = np.nan
matches.to_csv(OUT/'matches_2022_2025.csv', index=False)

# Overview: service, return, winners/errors
ov = add_match_meta(read_csv('charting-m-stats-Overview.csv'), matches)
ov = ov[ov['set'].astype(str).str.lower().eq('total')].copy()
num_cols = ['serve_pts','aces','dfs','first_in','first_won','second_in','second_won','bk_pts','bp_saved','return_pts','return_pts_won','winners','winners_fh','winners_bh','unforced','unforced_fh','unforced_bh']
for c in num_cols:
    ov[c] = pd.to_numeric(ov[c], errors='coerce').fillna(0)
ov['first_in_pct'] = np.where(ov['serve_pts']>0, ov['first_in']/ov['serve_pts'], np.nan)
ov['first_won_pct'] = np.where(ov['first_in']>0, ov['first_won']/ov['first_in'], np.nan)
ov['second_won_pct'] = np.where(ov['second_in']>0, ov['second_won']/ov['second_in'], np.nan)
ov['return_won_pct'] = np.where(ov['return_pts']>0, ov['return_pts_won']/ov['return_pts'], np.nan)
ov['bp_saved_pct'] = np.where(ov['bk_pts']>0, ov['bp_saved']/ov['bk_pts'], np.nan)
ov['winner_ue_ratio'] = np.where(ov['unforced']>0, ov['winners']/ov['unforced'], np.nan)
ov.to_csv(OUT/'overview_player_match_2022_2025.csv', index=False)

player_summary = ov.groupby('player', as_index=False).agg(
    matches=('match_id','nunique'), serve_pts=('serve_pts','sum'), aces=('aces','sum'), dfs=('dfs','sum'),
    first_in=('first_in','sum'), first_won=('first_won','sum'), second_in=('second_in','sum'), second_won=('second_won','sum'),
    bk_pts=('bk_pts','sum'), bp_saved=('bp_saved','sum'), return_pts=('return_pts','sum'), return_pts_won=('return_pts_won','sum'),
    winners=('winners','sum'), winners_fh=('winners_fh','sum'), winners_bh=('winners_bh','sum'), unforced=('unforced','sum')
)
for c in ['first_in_pct','first_won_pct','second_won_pct','return_won_pct','bp_saved_pct','winner_ue_ratio']:
    pass
player_summary['first_in_pct'] = player_summary['first_in']/player_summary['serve_pts']
player_summary['first_won_pct'] = player_summary['first_won']/player_summary['first_in']
player_summary['second_won_pct'] = player_summary['second_won']/player_summary['second_in']
player_summary['return_won_pct'] = player_summary['return_pts_won']/player_summary['return_pts']
player_summary['bp_saved_pct'] = player_summary['bp_saved']/player_summary['bk_pts'].replace(0,np.nan)
player_summary['winner_ue_ratio'] = player_summary['winners']/player_summary['unforced'].replace(0,np.nan)
player_summary = player_summary.sort_values(['matches','winner_ue_ratio'], ascending=False)
player_summary.to_csv(OUT/'player_summary_2022_2025.csv', index=False)

al = ov[ov['player'].eq(ALCARAZ)].copy()
al.to_csv(OUT/'alcaraz_match_level_2022_2025.csv', index=False)
al_year = al.groupby('year', as_index=False).agg(matches=('match_id','nunique'), serve_pts=('serve_pts','sum'), aces=('aces','sum'), dfs=('dfs','sum'), first_in=('first_in','sum'), first_won=('first_won','sum'), second_in=('second_in','sum'), second_won=('second_won','sum'), return_pts=('return_pts','sum'), return_pts_won=('return_pts_won','sum'), winners=('winners','sum'), unforced=('unforced','sum'), bk_pts=('bk_pts','sum'), bp_saved=('bp_saved','sum'))
for pct_name, n, d in [('first_in_pct','first_in','serve_pts'),('first_won_pct','first_won','first_in'),('second_won_pct','second_won','second_in'),('return_won_pct','return_pts_won','return_pts'),('bp_saved_pct','bp_saved','bk_pts')]:
    al_year[pct_name] = al_year[n]/al_year[d].replace(0,np.nan)
al_year['winner_ue_ratio'] = al_year['winners']/al_year['unforced'].replace(0,np.nan)
al_year.to_csv(OUT/'alcaraz_year_summary_2022_2025.csv', index=False)

surf = al.groupby('Surface', as_index=False).agg(matches=('match_id','nunique'), serve_pts=('serve_pts','sum'), aces=('aces','sum'), first_in=('first_in','sum'), first_won=('first_won','sum'), second_in=('second_in','sum'), second_won=('second_won','sum'), return_pts=('return_pts','sum'), return_pts_won=('return_pts_won','sum'), winners=('winners','sum'), unforced=('unforced','sum'))
surf['first_won_pct']=surf['first_won']/surf['first_in'].replace(0,np.nan)
surf['return_won_pct']=surf['return_pts_won']/surf['return_pts'].replace(0,np.nan)
surf['winner_ue_ratio']=surf['winners']/surf['unforced'].replace(0,np.nan)
surf.to_csv(OUT/'alcaraz_surface_summary_2022_2025.csv', index=False)

# Rallies
rally = add_match_meta(read_csv('charting-m-stats-Rally.csv'), matches)
for c in ['pts','pl1_won','pl1_winners','pl1_forced','pl1_unforced','pl2_won','pl2_winners','pl2_forced','pl2_unforced']:
    rally[c]=pd.to_numeric(rally[c], errors='coerce').fillna(0)
# Convert server/returner and pl1/pl2 columns to player perspective by stacking rows
r1 = rally[['match_id','year','Tournament','Surface','row','server','pts','pl1_won','pl1_winners','pl1_forced','pl1_unforced']].rename(columns={'server':'player','pl1_won':'pts_won','pl1_winners':'winners','pl1_forced':'forced','pl1_unforced':'unforced'})
r2 = rally[['match_id','year','Tournament','Surface','row','returner','pts','pl2_won','pl2_winners','pl2_forced','pl2_unforced']].rename(columns={'returner':'player','pl2_won':'pts_won','pl2_winners':'winners','pl2_forced':'forced','pl2_unforced':'unforced'})
rally_player = pd.concat([r1,r2], ignore_index=True)
rally_player['pts_won_pct'] = rally_player['pts_won']/rally_player['pts'].replace(0,np.nan)
rally_player.to_csv(OUT/'rally_player_segments_2022_2025.csv', index=False)
rally_player[rally_player['player'].eq(ALCARAZ)].to_csv(OUT/'alcaraz_rally_segments_2022_2025.csv', index=False)

# Shot types
shot = add_match_meta(read_csv('charting-m-stats-ShotTypes.csv'), matches)
for c in ['shots','pt_ending','winners','induced_forced','unforced','serve_return','shots_in_pts_won','shots_in_pts_lost']:
    shot[c]=pd.to_numeric(shot[c], errors='coerce').fillna(0)
shot['winner_per_100_shots'] = 100*shot['winners']/shot['shots'].replace(0,np.nan)
shot['ue_per_100_shots'] = 100*shot['unforced']/shot['shots'].replace(0,np.nan)
shot.to_csv(OUT/'shot_types_player_match_2022_2025.csv', index=False)
shot_al = shot[shot['player'].eq(ALCARAZ)].groupby('row', as_index=False).agg(shots=('shots','sum'), winners=('winners','sum'), unforced=('unforced','sum'), pt_ending=('pt_ending','sum'), matches=('match_id','nunique'))
shot_al['winner_per_100_shots']=100*shot_al['winners']/shot_al['shots'].replace(0,np.nan)
shot_al['ue_per_100_shots']=100*shot_al['unforced']/shot_al['shots'].replace(0,np.nan)
shot_al.sort_values('shots', ascending=False).to_csv(OUT/'alcaraz_shot_types_summary_2022_2025.csv', index=False)

# Serve direction and return outcomes, net points aggregate
for src,outname in [('charting-m-stats-ServeDirection.csv','serve_direction_player_match_2022_2025.csv'),('charting-m-stats-ReturnOutcomes.csv','return_outcomes_player_match_2022_2025.csv'),('charting-m-stats-NetPoints.csv','net_points_player_match_2022_2025.csv'),('charting-m-stats-KeyPointsReturn.csv','key_points_return_player_match_2022_2025.csv'),('charting-m-stats-ShotDirection.csv','shot_direction_player_match_2022_2025.csv'),('charting-m-stats-ServeBasics.csv','serve_basics_player_match_2022_2025.csv')]:
    df = add_match_meta(read_csv(src), matches)
    df.to_csv(OUT/outname, index=False)

# points sample filtered, only metadata and point winners for app previews (not all heavy columns)
pts_iter = pd.read_csv(RAW/'charting-m-points-2020s.csv', chunksize=300000, low_memory=False)
keep = []
midset = set(matches['match_id'])
for chunk in pts_iter:
    chunk = chunk[chunk['match_id'].isin(midset)]
    if not chunk.empty:
        keep.append(chunk[['match_id','Pt','Set1','Set2','Gm1','Gm2','Pts','Svr','PtWinner']])
points = pd.concat(keep, ignore_index=True) if keep else pd.DataFrame()
points = points.merge(matches[['match_id','year','Tournament','Surface','Player 1','Player 2']], on='match_id', how='left')
points.to_csv(OUT/'points_sample_2022_2025.csv', index=False)

summary = {
    'matches_2022_2025': int(matches['match_id'].nunique()),
    'players_with_overview_stats': int(player_summary['player'].nunique()),
    'alcaraz_matches': int(al['match_id'].nunique()),
    'alcaraz_years': ', '.join(map(str, sorted(al['year'].dropna().unique().astype(int)))) if not al.empty else 'N/A',
    'point_rows_2022_2025': int(len(points)),
}
pd.DataFrame([summary]).to_csv(OUT/'project_summary.csv', index=False)
print(summary)
