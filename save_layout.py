"""DSTS Save File Layout — Complete reverse-engineered structure map.

Every known offset, struct, region, and field in the Digimon Story: Time Stranger
save file. This module is both documentation AND code — import it to use the
constants directly in memory_reader.py or any save file tool.

Save file encryption: AES-128-ECB
Key: 33393632373736373534353535383833 (ASCII: 3962776754555883)
Total size: 3,098,176 bytes (2.95 MB)

Last updated: 2026-03-17
"""

# ══════════════════════════════════════════════════════════════════════
# ENCRYPTION
# ══════════════════════════════════════════════════════════════════════

AES_KEY_HEX = '33393632373736373534353535383833'
AES_KEY_ASCII = '3962776754555883'
AES_MODE = 'ECB'  # AES-128-ECB, same scheme as Cyber Sleuth

# Save file locations (relative to Steam install)
SAVE_LOCAL = 'gamedata/savedata/{steam_id}/0000.bin'      # autosave
SAVE_CLOUD = 'userdata/{user_id}/1984270/remote/savedata00.dat'
STEAM_APP_ID = 1984270

# ══════════════════════════════════════════════════════════════════════
# SAVE FILE REGIONS
# ══════════════════════════════════════════════════════════════════════
# Each tuple: (start, end, description)
# Offsets are into the DECRYPTED data.

REGIONS = {
    # ── Header & Metadata ──
    'header':           (0x000000, 0x000100, 'Plaintext CSV header — play time, date, party stats'),
    'header_padding':   (0x000100, 0x000400, 'Empty (all zeros)'),
    'bitmask_digimon':  (0x000400, 0x000600, 'Field guide bitmask — 311 bits = Digimon seen flags'),
    'bitmask_extended': (0x000600, 0x000900, 'Extended bitmask — 378 more bits (items, skills, quests?)'),
    'battle_count':     (0x000900, 0x000904, 'Total battle/encounter count (Int32, unique location)'),
    'pre_roster_pad':   (0x000904, 0x001000, 'Empty padding before roster'),

    # ── Digimon Roster ──
    'roster_party_box': (0x001000, 0x009000, 'Digimon roster — party + box (~87 entries, stride 0x150)'),
    'roster_empty':     (0x009000, 0x053000, 'Pre-allocated empty box slots (94% zero)'),
    'roster_farm':      (0x053000, 0x055000, 'Digimon roster — farm entries (~13 entries)'),
    'roster_farm_empty':(0x055000, 0x05C000, 'Empty farm slots'),
    'scan_data':        (0x05C100, 0x05C900, 'SCAN PERCENTAGE TABLE — 397 (Int16 digi_id, Int16 scan_pct) pairs at stride 4. Values 0-200%. Cleared to 0 on scan conversion'),
    'roster_special':   (0x05C000, 0x05C100, 'Special roster header'),
    'special_entry':    (0x05C900, 0x060000, 'Aegiochusmon entry + special roster data'),

    # ── Event / History Data ──
    'event_padding':    (0x060000, 0x061140, 'Empty slots'),
    'party_history':    (0x061140, 0x061800, 'Party formation history — 44 quad snapshots of Digimon IDs'),
    'quest_completion':  (0x061800, 0x06E300, 'Quest completion log — stride 0x40, sentinel=0xFFFFFFFF. 26 filled slots. First Int32 = event ID (20xxx), second = Float32 ROTATION ANGLE (radians: pi/6, pi/2, etc = compass facing when event occurred). +0x14=flag, +0x3C=area/chapter ID'),
    'acquisition_log':  (0x06E300, 0x070000, 'Item/reward acquisition log — 116 entries with card drops'),
    'crafting_history':  (0x070000, 0x078000, 'Crafting/item history — 12 GIM-delimited record groups'),
    'discovery_table':  (0x078000, 0x079900, 'Entity discovery table — 200 (flag, id) pairs'),

    # ── Unknown / Sparse Regions ──
    'encounter_catalog': (0x080000, 0x09C000, 'Per-Digimon encounter catalog — stride 0x1000. STATIC (never changes between saves). Lists which enemies each Digimon CAN encounter. First Int32=Digimon ID, then (0xFFFF, enemy_id) pairs. ~23 entries for story/party Digimon'),
    'unlock_padding':   (0x09C000, 0x0A49A8, 'Empty (all zeros)'),
    'entity_unlocks':   (0x0A49A8, 0x0A4CA0, 'Entity unlock flags — 93 (id, 1) pairs, IDs 233-335'),

    # ── Agent / Player Data ──
    'agent_info_base':  (0x0FDE80, 0x0FE080, 'AgentInfoBase — player stats, money, TP, rank'),
    'game_state':       (0x0FE080, 0x106000, 'Game state — scene IDs, camera, spawn points, agent skills, item catalog'),
    'sentinel_10A':     (0x10A000, 0x10B000, 'Sentinel array (0xFFFFFFFF pairs) — empty equipment slots?'),
    'encounter_state':  (0x10D000, 0x114000, 'Battle/encounter state — position floats + encounter flags. Flags (0/1) toggle per battle. Contains 3D coordinates (float32) that change with player movement. ~28KB active'),

    # ── Per-Area Tracking ──
    'area_encounters':  (0x15C000, 0x1DC000, 'Per-area encounter tracking — stride ~0x1000, sentinel-separated'),
    'quest_state':      (0x1CF000, 0x1CF040, 'Current quest/mission state: [Lunamon=2, Agumon=50, 0, 2050]'),

    # ── Field Guide ──
    'field_guide':      (0x200000, 0x210000, 'Digimon Encyclopedia — 1394 (id, seen_flag) pairs'),

    # ── Dialogue ──
    'dialogue_cache':   (0x223000, 0x2F3000, 'NPC dialogue history/cache — ~800KB of text'),
}

# Total bitmask info
BITMASK_TOTAL_BITS = 689       # at 0x400-0x900
FIELD_GUIDE_TOTAL = 1394       # entries at 0x200000
FIELD_GUIDE_SEEN = 200         # entries with flag=1
DISCOVERY_TABLE_COUNT = 200    # at 0x078000
ENTITY_UNLOCK_COUNT = 93       # at 0x0A49A8


# ══════════════════════════════════════════════════════════════════════
# SAVE HEADER (plaintext CSV at offset 0x000)
# ══════════════════════════════════════════════════════════════════════
# The first ~120 bytes are an unencrypted ASCII string:
# "5, 3097152, 176, 0, Dan , 339499.831890, 300, 109,
#  { 716, 365, 220 }, {30, 28, 26 }, 0, 2026, 3, 17, 21, 56, 1, {135214}"

HEADER_FIELDS = {
    0:  ('save_version',     int,   'Save version or slot ID (5)'),
    1:  ('payload_size',     int,   'Encrypted payload size in bytes (3097152)'),
    2:  ('unknown_176',      int,   'Unknown (176)'),
    3:  ('unknown_0',        int,   'Unknown (0)'),
    4:  ('player_name',      str,   'Player name ("Dan")'),
    5:  ('play_time_sec',    float, 'Total play time in seconds (339499.83 = 94.3 hours)'),
    6:  ('unknown_300',      int,   'Unknown — max box size? game constant? (300)'),
    7:  ('digimon_count',    int,   'Total Digimon encountered (109)'),
    8:  ('party_abi',        list,  'Party ABI values {716, 365, 220} — matches +0x104 in roster'),
    9:  ('party_levels',     list,  'Party levels {30, 28, 26}'),
    10: ('unknown_0b',       int,   'Unknown (0)'),
    11: ('save_year',        int,   'Save year (2026)'),
    12: ('save_month',       int,   'Save month (3)'),
    13: ('save_day',         int,   'Save day (17)'),
    14: ('save_hour',        int,   'Save hour (21)'),
    15: ('save_minute',      int,   'Save minute (56)'),
    16: ('unknown_1',        int,   'Unknown — difficulty? NG+ flag? (1)'),
    17: ('unknown_checksum', int,   'Unknown — found at 0x201D3C in field guide region (135214)'),
}


# ══════════════════════════════════════════════════════════════════════
# AGENT INFO BASE (player data)
# ══════════════════════════════════════════════════════════════════════
# Anchor: search for player name at +0x10, validate money/rank.
# Base offset in current save: 0x0FDE80

AGENT_BASE_OFFSET = 0x0FDE80  # varies per save, found by name search

# Offsets relative to agent base
AGENT = {
    # fmt: (offset, type, field_name, description, status)
    # type: 'I'=uint32, 'i'=int32, 'f'=float, 's'=string, 'B'=byte
    'player_name':   (0x010, 's',  'Player name (ASCII, null-terminated, ~32 bytes)',       'USED'),
    'play_time_dbl':  (0x050, 'd',  'CONFIRMED: Play time as Float64 (double). Matches header CSV value exactly: 342510.027029 seconds = 95.1 hours. Updated on every save', 'HIGH', 'read_not_displayed'),
    'money':         (0x058, 'I',  'Money (yen)',                                            'read_not_displayed'),
    'tp_available':  (0x05C, 'I',  'CONFIRMED: Available/unspent Tamer Points. Decreases when skills purchased (455->410 = -45 from buying 1 Valor skill). Separate from +0x060 total TP', 'HIGH', 'read_not_displayed'),
    'tamer_points':  (0x060, 'I',  'Tamer Points (TP)',                                      'read_not_displayed'),
    'agent_rank':    (0x064, 'I',  'Agent Rank (1-100)',                                     'USED'),
    'valor_count':   (0x068, 'I',  'Valor skill count',                                      'logged'),
    'phil_count':    (0x06C, 'I',  'Philanthropy skill count',                                'logged'),
    'amic_count':    (0x070, 'I',  'Amicability skill count',                                 'logged'),
    'wisdom_count':  (0x074, 'I',  'Wisdom skill count',                                     'logged'),
    # 0x078, 0x07C = zero gap
    'loyalty_count': (0x080, 'I',  'Loyalty skill count',                                    'logged'),
    # 0x084-0x088 = zero gap
    'sentinel':      (0x08C, 'I',  'Sentinel (-1 = 0xFFFFFFFF) — validation marker',         'USED'),
    'unknown_090':   (0x090, 'I',  'Unknown (655509760)',                                    'noted'),
}

# Agent skill records: 208 entries at base + 30560, stride 12
AGENT_SKILL_OFFSET = 30560     # 0x7760
AGENT_SKILL_STRIDE = 12
AGENT_SKILL_COUNT = 208

# Per-skill record layout (12 bytes)
AGENT_SKILL_RECORD = {
    'tree_group':  (0, 'I',  'Skill tree group ID (1-224)'),
    'category':    (4, 'I',  'Category: 1=Valor, 2=Phil, 3=Amic, 4=Wisdom, 5=Loyalty'),
    'purchased':   (8, 'B',  'Purchased flag (0 or 1)'),
    'visible':     (9, 'B',  'Visible/unlocked flag'),
    'unknown_flag':(10,'B',  'Unknown flag'),
    'padding':     (11,'B',  'Padding byte'),
}

# Tree group ranges
SKILL_TREE_RANGES = {
    'valor':        (1, 46),
    'philanthropy': (51, 96),
    'amicability':  (101, 146),
    'wisdom':       (151, 196),
    'loyalty':      (201, 224),
}

# Stat boost cost codes (tamer_skills.cost -> stat name)
STAT_COST_MAP = {16: 'hp', 17: 'sp', 18: 'atk', 19: 'def', 20: 'int', 21: 'spi', 22: 'spd'}

# Stat boost tiers (cumulative percentage)
STAT_BOOST_TIERS = {1: 0.20, 2: 0.45, 3: 0.75}

# Loyalty tree_group -> stage names
LOYALTY_STAGES = {
    215: ('In-Training I', 'In-Training II'),
    216: ('Rookie',),
    217: ('Champion', 'Armor'),
    218: ('Ultimate', 'Hybrid', 'Mega', 'Ultra'),
}

# Loyalty flat bonus per rank
LOYALTY_FLAT_BONUS = {
    215: {'hp': 200, 'sp': 200, 'other': 25},   # In-Training I/II
    216: {'hp': 150, 'sp': 150, 'other': 20},   # Rookie
    217: {'hp': 100, 'sp': 100, 'other': 15},   # Champion/Armor
    218: {'hp': 50,  'sp': 50,  'other': 10},   # Ultimate/Hybrid/Mega/Ultra
}

# Perfection tree_group -> personality_id
PERFECTION_MAP = {
    # Valor
    37: 1,   # Brave
    28: 2,   # Zealous
    44: 3,   # Daring
    14: 4,   # Reckless
    # Philanthropy
    67: 5,   # Adoring
    96: 6,   # Devoted
    86: 7,   # Tolerant
    72: 8,   # Overprotective
    # Amicability
    117: 9,  # Compassionate
    146: 10, # Sociable
    134: 11, # Friendly
    123: 12, # Opportunistic
    # Wisdom
    180: 13, # Astute
    172: 14, # Strategic
    184: 15, # Enlightened
    193: 16, # Sly
}


# ══════════════════════════════════════════════════════════════════════
# AGENT BASE EXTENDED REGION (base+0x200 to base+0x7760)
# ══════════════════════════════════════════════════════════════════════
# ~30KB of game state persistence. Contains current scene, camera,
# and event script references. 61 non-zero data runs found.

GAME_STATE_STRINGS = {
    # Offset relative to agent base -> string found
    0x0200: '0_dbef_210',                  # Scene definition (truncated)
    0x032E: 'start_70',                    # Spawn/checkpoint ID
    0x0444: 'common019',                   # Common event script
    0x0544: 'common031',                   # Common event script
    0x0644: 'common029',                   # Common event script
    0x07E8: 'cam01_railcam',              # Camera type (rail camera)
    0x07F6: 'm210',                        # Map/scene ID
    0x08E8: 'followcam_default_loc',      # Default follow camera
    0x0A00: 'A2020_dbef_210',             # Full scene ID (area 2020, type dbef, instance 210)
    0x0D0C: 'X2028_daft_20',             # Another scene reference
    0x2DB0: 'start_50',                    # Another spawn point
}


# ══════════════════════════════════════════════════════════════════════
# DIGIMON COMPACT STRUCT (stride 0x150 = 336 bytes)
# ══════════════════════════════════════════════════════════════════════
# Located in roster regions. db_id at offset -4 relative to name start.
# 100 entries found in current save.

DIGI_STRIDE = 0x150  # 336 bytes per entry

# Complete field map — every byte accounted for.
# fmt: field_name: (offset, type, description, confidence, status)
# offset is relative to the name start (where ASCII name begins)
# type: 'I'=uint32, 'i'=int32, 'H'=uint16, 'h'=int16, 'B'=byte, 'f'=float, 's'=string
# confidence: HIGH, MEDIUM, LOW
# status: USED, NEW, NOTED, CONFIRMED_EMPTY

DIGI = {
    # ── Identity ──
    'db_id':            (-0x04, 'I',  'Database ID (matches digimon.id in DB)',              'HIGH',   'USED'),
    'name':             (0x000, 's',  'Name/nickname (ASCII, null-term, 32 bytes max)',      'HIGH',   'USED'),
    'name_padding':     (0x020, None, '64 bytes — CONFIRMED ALL ZEROS for all 100 entries',  'HIGH',   'CONFIRMED_EMPTY'),

    # ── Level & Experience ──
    'level':            (0x060, 'I',  'Level (1-99)',                                        'HIGH',   'USED'),
    'total_exp':        (0x064, 'I',  'Total accumulated EXP',                               'HIGH',   'USED'),
    'prev_form_exp':    (0x068, 'I',  'CONFIRMED: Previous forms total EXP. Zero until first digivolution, then stores the EXP the Digimon had before evolving. Verified by save-diff: Pabumon EXP 41322 moved here after evo to Tanemon', 'HIGH', 'NEW'),
    'cur_hp':           (0x06C, 'I',  'Current HP (validates non-empty entry)',               'HIGH',   'USED'),
    'cur_sp':           (0x070, 'I',  'Current SP',                                          'HIGH',   'USED'),

    # ── White Stats (growth + personality, 7 x Int32) ──
    'white_hp':         (0x074, 'I',  'HP white stat (growth + personality component)',       'HIGH',   'USED'),
    'white_sp':         (0x078, 'I',  'SP white stat',                                       'HIGH',   'USED'),
    'white_atk':        (0x07C, 'I',  'ATK white stat',                                      'HIGH',   'USED'),
    'white_def':        (0x080, 'I',  'DEF white stat',                                      'HIGH',   'USED'),
    'white_int':        (0x084, 'I',  'INT white stat',                                      'HIGH',   'USED'),
    'white_spi':        (0x088, 'I',  'SPI white stat',                                      'HIGH',   'USED'),
    'white_spd':        (0x08C, 'I',  'SPD white stat',                                      'HIGH',   'USED'),

    # ── Farm Training Bonus (7 x Int32, stored x10) ──
    'farm_hp':          (0x090, 'i',  'HP farm training bonus (divide by 10 for display)',    'HIGH',   'USED'),
    'farm_sp':          (0x094, 'i',  'SP farm training bonus',                               'HIGH',   'USED'),
    'farm_atk':         (0x098, 'i',  'ATK farm training bonus',                              'HIGH',   'USED'),
    'farm_def':         (0x09C, 'i',  'DEF farm training bonus',                              'HIGH',   'USED'),
    'farm_int':         (0x0A0, 'i',  'INT farm training bonus',                              'HIGH',   'USED'),
    'farm_spi':         (0x0A4, 'i',  'SPI farm training bonus',                              'HIGH',   'USED'),
    'farm_spd':         (0x0A8, 'i',  'SPD farm training bonus',                              'HIGH',   'USED'),

    # ── Blue Stats (evolution/training bonuses, 7 x Int32) ──
    'blue_hp':          (0x0AC, 'i',  'HP blue stat (evolution bonuses)',                     'HIGH',   'USED'),
    'blue_sp':          (0x0B0, 'i',  'SP blue stat',                                        'HIGH',   'USED'),
    'blue_atk':         (0x0B4, 'i',  'ATK blue stat',                                       'HIGH',   'USED'),
    'blue_def':         (0x0B8, 'i',  'DEF blue stat',                                       'HIGH',   'USED'),
    'blue_int':         (0x0BC, 'i',  'INT blue stat',                                        'HIGH',   'USED'),
    'blue_spi':         (0x0C0, 'i',  'SPI blue stat',                                       'HIGH',   'USED'),
    'blue_spd':         (0x0C4, 'i',  'SPD blue stat',                                       'HIGH',   'USED'),

    # ── Evolution / Type Metadata ──
    'player_evo_fwd':   (0x0C8, 'B',  'CONFIRMED: Forward digivolutions performed BY PLAYER only. 0 for Armor types, recruited Digimon, and de-digivolved forms. Does NOT count de-digi or wild chains', 'HIGH', 'NEW'),
    'c9_pad':           (0x0C9, 'B',  'Zero padding',                                        'HIGH',   'CONFIRMED_EMPTY'),
    'ca_pad':           (0x0CA, 'B',  'Zero padding',                                        'HIGH',   'CONFIRMED_EMPTY'),
    'cb_pad':           (0x0CB, 'B',  'Zero padding',                                        'HIGH',   'CONFIRMED_EMPTY'),
    'cc_const':         (0x0CC, 'B',  'Always 2 (constant across all entries)',               'HIGH',   'NOTED'),
    'cd_pad':           (0x0CD, 'B',  'Zero',                                                'HIGH',   'CONFIRMED_EMPTY'),
    'ce_party_slot':    (0x0CE, 'B',  'CONFIRMED STATIC: Party slot assignment at creation (0-5). Never changes across 9 saves. Set once when Digimon first placed in party', 'HIGH', 'NEW'),
    'cf_pad':           (0x0CF, 'B',  'Zero',                                                'HIGH',   'CONFIRMED_EMPTY'),

    # ── Training Timer (Farm only) / Zero Padding (Party/Box) ──
    # CORRECTION: Load Enhancement feeds into BLUE STATS (+0xAC-0xC4), NOT here.
    # Earlier "enhancement stat" observations were roster-shift artifacts.
    # Verified: Divermon enhanced with DoruGreymon — blue stats changed, +0xD0-0xEC unchanged.
    'training_timer':   (0x0D0, 'd',  'Farm only: Float64 training timer (~9.29-9.31). Zero for party/box', 'HIGH', 'NEW'),
    'training_status':  (0x0D8, 'I',  'Farm only: training status (hi=0x01 active, lo=session count). Zero for party/box', 'HIGH', 'NEW'),
    'dc_pad':           (0x0DC, 'I',  'Zero for party/box. Part of farm training data', 'LOW', 'NOTED'),
    'e0_pad':           (0x0E0, 'I',  'Zero for party/box', 'LOW', 'NOTED'),
    'e4_pad':           (0x0E4, 'I',  'Zero for party/box', 'LOW', 'NOTED'),
    'e8_pad':           (0x0E8, 'I',  'Zero for party/box', 'LOW', 'NOTED'),
    'personality_packed':(0x0EC,'I',  'Personality ID in HIGH BYTE (verified = +0xEE). Low bytes zero', 'HIGH', 'NEW'),

    # ── Personality ──
    'personality_id':   (0x0EE, 'B',  'Personality ID (1-16)',                                'HIGH',   'USED'),
    'ef_pad':           (0x0EF, 'B',  'Zero',                                                'HIGH',   'CONFIRMED_EMPTY'),

    # ── Capture Location / Origin ──
    'origin_area_1':    (0x0F0, 'I',  'Capture area indicator 1 (0-127). Digimon caught in same area have same value. Encodes WHERE obtained', 'HIGH', 'NEW'),
    'origin_area_2':    (0x0F4, 'I',  'Capture area indicator 2 (0-127). Paired with F0 to form area+sub-area. Same batch = same values', 'HIGH', 'NEW'),
    'origin_slot':      (0x0F8, 'I',  'Capture slot/encounter index (1-78). Varies slightly within same-area batches. Sub-area or encounter slot', 'MEDIUM', 'NEW'),
    'game_tick':         (0x0FC, 'I',  'CONFIRMED: Global game tick counter. Increments by +35 for ALL Digimon per battle (+500 on digivolution). Tracks overall game progression state. Range 27525-81560. NOT per-Digimon — same delta applied globally', 'HIGH', 'NEW'),

    # ── Talent & ABI ──
    'talent_raw':       (0x100, 'I',  'Talent (stored x1000, divide for display)',            'HIGH',   'USED'),
    'db_id_copy':       (0x104, 'I',  'CONFIRMED: Duplicate of db_id at -0x04. Verified 100/100 match. Game stores species ID twice — once in parent array, once in entry data', 'HIGH', 'NEW'),

    # ── Unknown Bonus Fields ──
    'evo_history_1':    (0x108, 'I',  'CONFIRMED: Evolution history — previous form db_id. Pabumon(387)->Tanemon(512): +0x108 became 387', 'HIGH', 'NEW'),
    'evo_history_2':    (0x10C, 'I',  'Evolution history — 2nd previous form. e.g. ExVeemon<-Veemon<-Tsunomon: Tsunomon here', 'HIGH', 'NEW'),
    'evo_history_3':    (0x110, 'I',  'Evolution history — 3rd previous form. Up to 5 forms stored', 'HIGH', 'NEW'),
    'evo_history_4':    (0x114, 'I',  'Evolution history — 4th previous form', 'HIGH', 'NEW'),
    'evo_history_5':    (0x118, 'I',  'Evolution history — 5th previous form. DoruGreymon chain: Growlmon<-Guilmon<-GeoGreymon<-Guilmon<-Koromon', 'HIGH', 'NEW'),
    'in_active_party':  (0x11C, 'I',  'CONFIRMED: In active party flag. Flag=1 for all 11 party members (all have skills). Flag=0 for box/farm (90 entries). Determines if Digimon is currently in battle party', 'HIGH', 'NEW'),

    # ── Attachment Skills (4 slots, each Int16 skill + Int16 padding) ──
    'attach_skill_1':   (0x120, 'H',  'Attachment skill 1 — game skill ID (30000+ range)',    'HIGH',   'NEW'),
    'attach_pad_1':     (0x122, 'H',  'Always 0 (confirmed across all 4 save-diffs)',          'HIGH',   'CONFIRMED_EMPTY'),
    'attach_skill_2':   (0x124, 'H',  'Attachment skill 2',                                   'HIGH',   'NEW'),
    'attach_pad_2':     (0x126, 'H',  'Always 0',                                             'HIGH',   'CONFIRMED_EMPTY'),
    'attach_skill_3':   (0x128, 'H',  'Attachment skill 3',                                   'HIGH',   'NEW'),
    'attach_pad_3':     (0x12A, 'H',  'Always 0',                                             'HIGH',   'CONFIRMED_EMPTY'),
    'attach_skill_4':   (0x12C, 'H',  'Attachment skill 4',                                   'HIGH',   'NEW'),
    'attach_pad_4':     (0x12E, 'H',  'Always 0',                                             'HIGH',   'CONFIRMED_EMPTY'),

    # ── Equipment ──
    'equip_slot_1':     (0x130, 'H',  'Equipment slot 1 (item ID, 0=empty)',                  'HIGH',   'USED'),
    'equip_slot_2':     (0x132, 'H',  'Equipment slot 2 (item ID, 0=empty)',                  'HIGH',   'USED'),

    # ── Bond & Friendship ──
    'friendship_cap':   (0x134, 'f',  'Friendship/CAM ceiling. 100.0 for party, 0.0 for box/farm', 'HIGH', 'NEW'),
    'total_transforms': (0x138, 'I',  'CONFIRMED: Total transformation count incl de-digi. 0=never player-evolved (wild/recruited). 4-7=heavily transformed. Only set for player-evolved Digimon', 'HIGH', 'NEW'),
    'bond_raw':         (0x13C, 'f',  'Bond (stored as float, divide by 100 for percentage)', 'HIGH',   'USED'),

    # ── Roster Metadata ──
    'active_flag':      (0x140, 'I',  'Active flag (1=valid entry, 0=tail/empty)',            'HIGH',   'NEW'),
    'roster_index':     (0x144, 'I',  'Sequential roster index (0-80+). Exact box/party order', 'HIGH', 'NEW'),
    'creation_hash':    (0x148, 'I',  'Unique 32-bit hash per Digimon. RNG seed at creation or timestamp-based', 'HIGH', 'NEW'),
    'next_db_id':       (0x14C, 'I',  'CONFIRMED: db_id of next roster entry. Forward linked list pointer. 87/87 perfect match verified', 'HIGH', 'NEW'),
}

# Convenience: offset-only lookups for common fields
DIGI_DB_ID          = -0x04
DIGI_NAME           = 0x000
DIGI_LEVEL          = 0x060
DIGI_TOTAL_EXP      = 0x064
DIGI_PREV_FORM_EXP  = 0x068
DIGI_CUR_HP         = 0x06C
DIGI_CUR_SP         = 0x070
DIGI_WHITE_HP       = 0x074
DIGI_WHITE_SP       = 0x078
DIGI_WHITE_ATK      = 0x07C
DIGI_WHITE_DEF      = 0x080
DIGI_WHITE_INT      = 0x084
DIGI_WHITE_SPI      = 0x088
DIGI_WHITE_SPD      = 0x08C
DIGI_FARM_HP        = 0x090
DIGI_FARM_SP        = 0x094
DIGI_FARM_ATK       = 0x098
DIGI_FARM_DEF       = 0x09C
DIGI_FARM_INT       = 0x0A0
DIGI_FARM_SPI       = 0x0A4
DIGI_FARM_SPD       = 0x0A8
DIGI_BLUE_HP        = 0x0AC
DIGI_BLUE_SP        = 0x0B0
DIGI_BLUE_ATK       = 0x0B4
DIGI_BLUE_DEF       = 0x0B8
DIGI_BLUE_INT       = 0x0BC
DIGI_BLUE_SPI       = 0x0C0
DIGI_BLUE_SPD       = 0x0C4
DIGI_EVO_COUNT      = 0x0C8
DIGI_TRAINING_TIMER = 0x0D0   # Float64, farm only
DIGI_TRAINING_STATUS = 0x0D8  # Int32, farm only
DIGI_PERSONALITY     = 0x0EE
# NOTE: Load Enhancement feeds into BLUE STATS, not a separate field.
# Blue stats at +0xAC-0xC4 increase when a Digimon is fed via Load Enhancement.
DIGI_PERSONALITY_PACKED = 0x0EC
DIGI_ORIGIN_AREA_1  = 0x0F0
DIGI_ORIGIN_AREA_2  = 0x0F4
DIGI_ORIGIN_SLOT    = 0x0F8
DIGI_UNKNOWN_FC     = 0x0FC
DIGI_TALENT_RAW     = 0x100
DIGI_DB_ID_COPY     = 0x104
DIGI_EVO_HIST_1     = 0x108
DIGI_EVO_HIST_2     = 0x10C
DIGI_EVO_HIST_3     = 0x110
DIGI_EVO_HIST_4     = 0x114
DIGI_EVO_HIST_5     = 0x118
DIGI_ACTIVE_TRAINED = 0x11C
DIGI_ATTACH_SKILL_1 = 0x120
DIGI_ATTACH_SKILL_2 = 0x124
DIGI_ATTACH_SKILL_3 = 0x128
DIGI_ATTACH_SKILL_4 = 0x12C
DIGI_EQUIP_1        = 0x130
DIGI_EQUIP_2        = 0x132
DIGI_FRIENDSHIP_CAP = 0x134
DIGI_EVO_GENERATION = 0x138
DIGI_BOND_RAW       = 0x13C
DIGI_ACTIVE_FLAG    = 0x140
DIGI_ROSTER_INDEX   = 0x144
DIGI_CREATION_HASH  = 0x148
DIGI_NEXT_ABI       = 0x14C

# White/farm/blue stat offset lists (for iteration)
WHITE_STAT_OFFSETS = [0x074, 0x078, 0x07C, 0x080, 0x084, 0x088, 0x08C]
FARM_STAT_OFFSETS  = [0x090, 0x094, 0x098, 0x09C, 0x0A0, 0x0A4, 0x0A8]
BLUE_STAT_OFFSETS  = [0x0AC, 0x0B0, 0x0B4, 0x0B8, 0x0BC, 0x0C0, 0x0C4]
STAT_NAMES         = ['hp', 'sp', 'atk', 'def', 'int', 'spi', 'spd']

# Attachment skill ID ranges
SKILL_ID_BASIC   = (10011, 10013)   # Attack, Guard, Escape
SKILL_ID_SYSTEM  = (11013, 11014)   # Recoil, confusion
SKILL_ID_COMBAT  = (30000, 34999)   # Learned combat skills (what's stored at +0x120)
SKILL_ID_SUPPORT = (32000, 32999)   # Support/passive skills (subset of combat)
SKILL_ID_CHARGE  = (34000, 34999)   # Buff/charge skills (subset of combat)
SKILL_ID_SPECIAL = (70000, 70999)   # Special/story skills


# ══════════════════════════════════════════════════════════════════════
# ITEM CATALOG (at ~0x1055E0 relative to save start)
# ══════════════════════════════════════════════════════════════════════
# Note: actual offset depends on agent base. This is in the game_state region.

ITEM_CATALOG_OFFSET = 0x1055E0  # absolute offset in decrypted save
ITEM_CATALOG_STRIDE = 12
ITEM_CATALOG_COUNT = 208        # sequential IDs 1-224 with category gaps

# Per-item record layout (12 bytes)
ITEM_RECORD = {
    'item_id':   (0, 'I',  'Item ID (sequential, matches item_names.item_id in DB)'),
    'category':  (4, 'I',  'Category: 1=Recovery(1-46), 2=Boosts(51-96), 3=Food(101-146), 4=Materials(151-196), 5=Key(201-224)'),
    'flag_owned':    (8,  'B', 'Owned/obtained flag (0 or 1)'),
    'flag_available':(9,  'B', 'Available in shop flag (0 or 1)'),
    'flag_seen':     (10, 'B', 'Seen/discovered flag (0 or 1)'),
    'flag_pad':      (11, 'B', 'Always 0 (padding)'),
}

# Flag combination meanings (observed)
ITEM_FLAG_COMBOS = {
    (0, 0, 0, 0): 'Never encountered (117 items)',
    (0, 1, 1, 0): 'Seen/in shop, not currently held (36 items)',
    (1, 1, 1, 0): 'Owned + seen + available (49 items)',
    (0, 1, 0, 0): 'Edge case — Banana, etc. (6 items)',
}

# NOTE: Item QUANTITIES are NOT in this catalog.
# Quantities stored elsewhere — user has figured out separately.

ITEM_CATEGORIES = {
    1: ('Recovery',  1,   46),
    2: ('Boosts',    51,  96),
    3: ('Food/Farm', 101, 146),
    4: ('Materials', 151, 196),
    5: ('Key/Digi',  201, 224),
}


# ══════════════════════════════════════════════════════════════════════
# DISCOVERY TABLE (at 0x078000)
# ══════════════════════════════════════════════════════════════════════

DISCOVERY_TABLE_OFFSET = 0x078000
DISCOVERY_TABLE_STRIDE = 8       # (flag: Int32, entity_id: Int32)
DISCOVERY_TABLE_MAX = 432        # was 200 — extended to 0x078D80

# Entity ID types found in discovery table
DISCOVERY_ID_TYPES = {
    'digimon': 100,    # matched to digimon.id
    'items':   29,     # matched to item_names.item_id
    'unknown': 89,     # IDs that span crafting_recipes, tamer_skills, side_quests, etc.
    # Unknown IDs likely use a shared entity ID space across game systems
}


# ══════════════════════════════════════════════════════════════════════
# FIELD GUIDE / ENCYCLOPEDIA (at 0x200000)
# ══════════════════════════════════════════════════════════════════════

FIELD_GUIDE_OFFSET = 0x200000
FIELD_GUIDE_STRIDE = 8           # (entity_id: Int32, seen_flag: Int32)
# seen_flag: 1 = seen/encountered, 0 = not yet seen
# Total: 1394 entries, 200 seen, 1194 unseen
# Covers ALL game entities: Digimon, items, NPCs, events


# ══════════════════════════════════════════════════════════════════════
# PARTY FORMATION HISTORY (at 0x061140)
# ══════════════════════════════════════════════════════════════════════

PARTY_HISTORY_OFFSET = 0x061140
PARTY_HISTORY_STRIDE = 16        # 4 x Int32 (one Digimon ID per party slot)
PARTY_HISTORY_MAX = 44           # snapshots in current save
# Column layout: [member1, member2, story_partner, member3]
# story_partner is always Aegiomon (ID 183) in current save
# Traces every party change and evolution path through the game


# ══════════════════════════════════════════════════════════════════════
# ITEM ACQUISITION LOG (at 0x06E300)
# ══════════════════════════════════════════════════════════════════════

ACQUISITION_LOG_OFFSET = 0x06E300
ACQUISITION_LOG_SLOTS = 128      # total capacity
ACQUISITION_LOG_FILLED = 116     # in current save
# Each entry: sequential item index paired with card/reward ID and quantity
# Tracks every item obtained — what, when, and what card drop accompanied it


# ══════════════════════════════════════════════════════════════════════
# CRAFTING HISTORY (at 0x070000)
# ══════════════════════════════════════════════════════════════════════

CRAFTING_HISTORY_OFFSET = 0x070000
CRAFTING_HISTORY_END = 0x078000
GIM_MARKER = b'GIM'             # 0x47494D — separates record groups
GIM_MARKER_COUNT = 12           # in current save
# Gap sizes between markers: min=24, max=168, most common=24 bytes
# Contains item IDs (300-354 = materials), skill IDs (10000+ = cards),
# equipment IDs (1000+ = attachments), combat skill IDs (30000+)


# ══════════════════════════════════════════════════════════════════════
# PERSONALITY MAP
# ══════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════
# SCAN PERCENTAGE TABLE (at 0x05C100)
# ══════════════════════════════════════════════════════════════════════
# Stores scan progress for all encounteragle Digimon.
# Structure: (digimon_id: Int16, scan_percent: Int16) pairs at stride 4.
# Scan values 0-200%. Cleared to 0 when scan is converted to a Digimon.

SCAN_TABLE_OFFSET = 0x05C100
SCAN_TABLE_END = 0x05CA20     # extends past 0x5C900 — 583 entries total
SCAN_TABLE_STRIDE = 4          # (Int16 digi_id, Int16 scan_pct)
SCAN_TABLE_MAX_ENTRIES = 583   # covers all Digimon IDs
SCAN_TABLE_REAL_START = 130    # entries 0-129 are garbage header data

# When a scan reaches 100%+, the player can convert it to recruit that Digimon.
# On conversion: scan_pct set to 0, new Digimon entry created in roster.
# Max scan is 200%.


PERSONALITY_NAMES = {
    1:  'Brave',          2:  'Zealous',       3:  'Daring',        4:  'Reckless',
    5:  'Adoring',        6:  'Devoted',       7:  'Tolerant',      8:  'Overprotective',
    9:  'Compassionate',  10: 'Sociable',      11: 'Friendly',      12: 'Opportunistic',
    13: 'Astute',         14: 'Strategic',      15: 'Enlightened',   16: 'Sly',
}


# ══════════════════════════════════════════════════════════════════════
# REMAINING UNKNOWNS
# ══════════════════════════════════════════════════════════════════════

UNKNOWNS = {
    # Digimon struct fields
    # ALL SOLVED via save-diff:
    # 'digi_0x068': Previous form total EXP
    # 'digi_0x0F0/F4': Capture area indicators
    # 'digi_0x0F8': Capture encounter slot
    # 'digi_0x0FC': Global game tick
    # 'digi_0x108-0x118': Evolution history chain (5 slots, verified with full chains)

    # SOLVED: agent_0x05C = Available/unspent Tamer Points (decreases on skill purchase)

    # Header fields
    'header_6':     'Value 300. Game constant across ALL saves. Roster has 1120 slots total. Likely max display/UI capacity.',
    'header_17':    'Value {135214}. CONFIRMED CONSTANT across ALL save slots including different play times. Game version/format identifier, NOT player data. Mirrored at 0x201D3C.',

    # Bitmask
    'bitmask_400':  'CONFIRMED: Game event flags. +2 bits from entering a dungeon (bits 1033, 10041). 0 bits from skill purchase. 0 bits from NPC talk. Triggers on area entry, story events. 10240 total bits, ~700 set.',

    # Value at 0x900
    'value_0x900':  'CRACKED: Tracks field guide entity registration. Delta +8 = exact match with field guide total entries delta (1386->1394). Value = field_guide_total + 199. Grows when new entities (Digimon, items, recipes) are registered in the encyclopedia.',
}


# ══════════════════════════════════════════════════════════════════════
# FARM DIGIMON STRUCT (stride 0x158 — 8 bytes longer than party/box)
# ══════════════════════════════════════════════════════════════════════
# Farm entries at 0x053000-0x055000 use stride 0x158.
# The core Digimon fields (+0x000 to +0x14C) are identical to party/box,
# but the creation hash is at +0x150 (party/box uses +0x148) because
# +0x148 stores the farm slot index in farm entries.

FARM_STRIDE = 0x158

FARM_FIELDS = {
    # Farm Digimon share the same core struct layout as party/box.
    # Located at 0x053000-0x055000, stride 0x158.
    #
    # Training data lives at FIXED offsets within the standard struct:
    #   +0x0D0: Training timer (Float64, ~9.29-9.31 = game time scale)
    #   +0x0D8: Training status (Int32: high byte 0x01=active, 0x00=done, low 24 bits=session counter)
    #
    # These are the same bytes we initially labeled "padding/enhance" — they serve
    # DUAL PURPOSE: training timer for farm Digimon, enhancement data for party Digimon.
    #
    # Training bonus goes to the appropriate farm_stat field (+0x090-0x0A8):
    #   +300 per normal training session, +1000 for intensive
    #   Which stat gets the bonus depends on the training type selected
    #
    # Status decoding:
    #   0x01000016 = session 22 in-progress (high byte = 0x01)
    #   0x00000017 = session 23 completed (counter incremented, high byte cleared)
    #   0x01000008 = session 8 in-progress
    #
    # Empty farm slots: sentinels at +0x038-0x040, +0x054=5000
    'uses_same_struct': True,
    'training_timer_offset': 0x0D0,  # Float64, same as enhance HP/SP in party entries
    'training_status_offset': 0x0D8, # Int32, same as enhance ATK in party entries
}

# ══════════════════════════════════════════════════════════════════════
# SLOT FILES (plaintext, 720 bytes each)
# ══════════════════════════════════════════════════════════════════════
# slot_NNNN.bin — one per save slot, plaintext (NOT encrypted)
# Contains display metadata for the load screen:
#   +0x000: Slot label "#NN Unused text" (16 bytes)
#   +0x040: Player name "Dan" (16 bytes)
#   Play time as human-readable: "96Hours4Minutes"
# 720 bytes total, simple text + padding

# ══════════════════════════════════════════════════════════════════════
# SYSDATA (game settings, 992 bytes, AES encrypted)
# ══════════════════════════════════════════════════════════════════════
# sysdata_dx11.bin — system/game settings, same AES-128-ECB encryption
# Contains Int32 configuration values:
#   Audio volumes, brightness, control mappings, difficulty settings
#   Small values (1-92 range) at 0x130-0x190 = specific settings
SYSDATA_FILE = 'sysdata_dx11.bin'
SYSDATA_SIZE = 992

# ══════════════════════════════════════════════════════════════════════
# SPECIAL ROSTER HEADER (0x05C000-0x05C0C8)
# ══════════════════════════════════════════════════════════════════════
# Game progression markers and story partner setup:
#   +0x020-0x080: Area/chapter progression IDs (1-5), sentinels for locked areas
#   +0x088-0x090: Late-game/DLC flags
#   +0x0C8: Aegiochusmon entry start (standard Digimon struct)
SPECIAL_HEADER_OFFSET = 0x05C000
AEGIOCHUSMON_ENTRY = 0x05C0C8


FARM_TRAINING_ACTIVE = 0x01000000 # High byte mask for "training in progress"
FARM_BONUS_INCREMENT_NORMAL = 300
FARM_BONUS_INCREMENT_INTENSIVE = 1000
FARM_EMPTY_SLOT_MARKER = 5000     # Value at +0x054 for empty slots


# ══════════════════════════════════════════════════════════════════════
# SAVE-DIFF DISCOVERIES (2026-03-17)
# ══════════════════════════════════════════════════════════════════════

SAVE_DIFF_FINDINGS = {
    'training_diff': {
        'description': 'Pre-training vs post-training completion',
        'key_changes': [
            '+0x008 farm bonus: increments by +300 per session',
            '+0x034 training timer: float increasing by ~0.015',
            '+0x038 training status: high byte clears (0x01->0x00) on completion',
            '+0x03B flag: 1->0 on training complete',
            'Dialogue cache: ~50KB of training completion messages added',
        ],
    },
    'battle_diff': {
        'description': 'Pre-battle vs post-one-battle',
        'key_changes': [
            '+0x122/+0x126/+0x12A/+0x12E (skill usage counters): ALL Digimon increment by +35 per battle (global tick)',
            'Party Digimon EXP increased',
            'Party white stats updated (SPD changes observed)',
            'Header play_time increased by ~2 minutes',
            'Header save_minute updated',
            'Crafting history: 12 entries changed',
        ],
    },
    'evo_diff': {
        'description': 'Pre-evo vs post-digivolution',
        'key_changes': [
            'Digivolved Digimon: farm stats zeroed, blue stats zeroed (de-digi/re-digi reset)',
            'Attachment skills changed (new skills after evo)',
            'Equipment shifted between slots',
            'Aegiochusmon (story partner) entry updated',
            'Game state position data changed',
        ],
    },
}

