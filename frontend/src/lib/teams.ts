// Canonical NFL team identity: name, city, primary color, secondary color,
// ESPN logo URL. Used for visual consistency across every page of the
// dashboard. Colors sourced from public brand guidelines.

export type TeamMeta = {
  abbr: string;
  city: string;
  name: string;      // nickname, e.g. "Cardinals"
  full: string;      // city + name, e.g. "Arizona Cardinals"
  primary: string;   // hex
  secondary: string; // hex, used for subtle accents
  logo: string;      // ESPN CDN (public), 500px PNG
};

// ESPN logo CDN — stable and public. Some franchises use different team
// abbreviations here than our canonical set; the mapping is handled per-team.
const logoFor = (espnCode: string) =>
  `https://a.espncdn.com/i/teamlogos/nfl/500/${espnCode.toLowerCase()}.png`;

export const TEAMS: Record<string, TeamMeta> = {
  ARI: { abbr: 'ARI', city: 'Arizona',      name: 'Cardinals',  full: 'Arizona Cardinals',      primary: '#97233F', secondary: '#000000', logo: logoFor('ari') },
  ATL: { abbr: 'ATL', city: 'Atlanta',      name: 'Falcons',    full: 'Atlanta Falcons',        primary: '#A71930', secondary: '#000000', logo: logoFor('atl') },
  BAL: { abbr: 'BAL', city: 'Baltimore',    name: 'Ravens',     full: 'Baltimore Ravens',       primary: '#241773', secondary: '#9E7C0C', logo: logoFor('bal') },
  BUF: { abbr: 'BUF', city: 'Buffalo',      name: 'Bills',      full: 'Buffalo Bills',          primary: '#00338D', secondary: '#C60C30', logo: logoFor('buf') },
  CAR: { abbr: 'CAR', city: 'Carolina',     name: 'Panthers',   full: 'Carolina Panthers',      primary: '#0085CA', secondary: '#101820', logo: logoFor('car') },
  CHI: { abbr: 'CHI', city: 'Chicago',      name: 'Bears',      full: 'Chicago Bears',          primary: '#0B162A', secondary: '#C83803', logo: logoFor('chi') },
  CIN: { abbr: 'CIN', city: 'Cincinnati',   name: 'Bengals',    full: 'Cincinnati Bengals',     primary: '#FB4F14', secondary: '#000000', logo: logoFor('cin') },
  CLE: { abbr: 'CLE', city: 'Cleveland',    name: 'Browns',     full: 'Cleveland Browns',       primary: '#311D00', secondary: '#FF3C00', logo: logoFor('cle') },
  DAL: { abbr: 'DAL', city: 'Dallas',       name: 'Cowboys',    full: 'Dallas Cowboys',         primary: '#003594', secondary: '#869397', logo: logoFor('dal') },
  DEN: { abbr: 'DEN', city: 'Denver',       name: 'Broncos',    full: 'Denver Broncos',         primary: '#FB4F14', secondary: '#002244', logo: logoFor('den') },
  DET: { abbr: 'DET', city: 'Detroit',      name: 'Lions',      full: 'Detroit Lions',          primary: '#0076B6', secondary: '#B0B7BC', logo: logoFor('det') },
  GB:  { abbr: 'GB',  city: 'Green Bay',    name: 'Packers',    full: 'Green Bay Packers',      primary: '#203731', secondary: '#FFB612', logo: logoFor('gb')  },
  HOU: { abbr: 'HOU', city: 'Houston',      name: 'Texans',     full: 'Houston Texans',         primary: '#03202F', secondary: '#A71930', logo: logoFor('hou') },
  IND: { abbr: 'IND', city: 'Indianapolis', name: 'Colts',      full: 'Indianapolis Colts',     primary: '#002C5F', secondary: '#A2AAAD', logo: logoFor('ind') },
  JAX: { abbr: 'JAX', city: 'Jacksonville', name: 'Jaguars',    full: 'Jacksonville Jaguars',   primary: '#006778', secondary: '#9F792C', logo: logoFor('jax') },
  KC:  { abbr: 'KC',  city: 'Kansas City',  name: 'Chiefs',     full: 'Kansas City Chiefs',     primary: '#E31837', secondary: '#FFB81C', logo: logoFor('kc')  },
  LAC: { abbr: 'LAC', city: 'Los Angeles',  name: 'Chargers',   full: 'Los Angeles Chargers',   primary: '#0080C6', secondary: '#FFC20E', logo: logoFor('lac') },
  LAR: { abbr: 'LAR', city: 'Los Angeles',  name: 'Rams',       full: 'Los Angeles Rams',       primary: '#003594', secondary: '#FFA300', logo: logoFor('lar') },
  LV:  { abbr: 'LV',  city: 'Las Vegas',    name: 'Raiders',    full: 'Las Vegas Raiders',      primary: '#000000', secondary: '#A5ACAF', logo: logoFor('lv')  },
  MIA: { abbr: 'MIA', city: 'Miami',        name: 'Dolphins',   full: 'Miami Dolphins',         primary: '#008E97', secondary: '#FC4C02', logo: logoFor('mia') },
  MIN: { abbr: 'MIN', city: 'Minnesota',    name: 'Vikings',    full: 'Minnesota Vikings',      primary: '#4F2683', secondary: '#FFC62F', logo: logoFor('min') },
  NE:  { abbr: 'NE',  city: 'New England',  name: 'Patriots',   full: 'New England Patriots',   primary: '#002244', secondary: '#C60C30', logo: logoFor('ne')  },
  NO:  { abbr: 'NO',  city: 'New Orleans',  name: 'Saints',     full: 'New Orleans Saints',     primary: '#101820', secondary: '#D3BC8D', logo: logoFor('no')  },
  NYG: { abbr: 'NYG', city: 'New York',     name: 'Giants',     full: 'New York Giants',        primary: '#0B2265', secondary: '#A71930', logo: logoFor('nyg') },
  NYJ: { abbr: 'NYJ', city: 'New York',     name: 'Jets',       full: 'New York Jets',          primary: '#125740', secondary: '#000000', logo: logoFor('nyj') },
  PHI: { abbr: 'PHI', city: 'Philadelphia', name: 'Eagles',     full: 'Philadelphia Eagles',    primary: '#004C54', secondary: '#A5ACAF', logo: logoFor('phi') },
  PIT: { abbr: 'PIT', city: 'Pittsburgh',   name: 'Steelers',   full: 'Pittsburgh Steelers',    primary: '#FFB612', secondary: '#101820', logo: logoFor('pit') },
  SEA: { abbr: 'SEA', city: 'Seattle',      name: 'Seahawks',   full: 'Seattle Seahawks',       primary: '#002244', secondary: '#69BE28', logo: logoFor('sea') },
  SF:  { abbr: 'SF',  city: 'San Francisco',name: '49ers',      full: 'San Francisco 49ers',    primary: '#AA0000', secondary: '#B3995D', logo: logoFor('sf')  },
  TB:  { abbr: 'TB',  city: 'Tampa Bay',    name: 'Buccaneers', full: 'Tampa Bay Buccaneers',   primary: '#D50A0A', secondary: '#0A0A08', logo: logoFor('tb')  },
  TEN: { abbr: 'TEN', city: 'Tennessee',    name: 'Titans',     full: 'Tennessee Titans',       primary: '#0C2340', secondary: '#4B92DB', logo: logoFor('ten') },
  WAS: { abbr: 'WAS', city: 'Washington',   name: 'Commanders', full: 'Washington Commanders',  primary: '#5A1414', secondary: '#FFB612', logo: logoFor('was') },
};

export function teamMeta(abbr: string | null | undefined): TeamMeta | null {
  if (!abbr) return null;
  return TEAMS[abbr.toUpperCase()] ?? null;
}

// Position color coding, used on player badges in pick rows.
export const POSITION_COLORS: Record<string, string> = {
  QB:   '#7c5cff',
  RB:   '#f97316',
  WR:   '#eab308',
  TE:   '#a855f7',
  OT:   '#3b82f6',
  OL:   '#3b82f6',
  G:    '#3b82f6',
  C:    '#3b82f6',
  IOL:  '#3b82f6',
  EDGE: '#ef4444',
  IDL:  '#dc2626',
  DL:   '#dc2626',
  DT:   '#dc2626',
  NT:   '#dc2626',
  LB:   '#ec4899',
  CB:   '#22c55e',
  S:    '#14b8a6',
  DB:   '#22c55e',
  FB:   '#f97316',
  ATH:  '#8a93a6',
};

export function positionColor(pos: string | null | undefined): string {
  if (!pos) return '#8a93a6';
  return POSITION_COLORS[pos.toUpperCase()] ?? '#8a93a6';
}
