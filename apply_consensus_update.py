"""Update consensus_rank in prospects CSV with authoritative 4/20/26 list
from nflmockdraftdatabase.com/big-boards/2026/consensus-big-board-2026.

This updates the BENCHMARK we compare against — does NOT feed the
independent model's scoring (rank is in banned_prospect_columns).
"""
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).parent
PROS = ROOT / "data/processed/prospects_2026_enriched.csv"

CONSENSUS_4_20 = """\
1 Fernando Mendoza
2 Arvell Reese
3 David Bailey
4 Jeremiyah Love
5 Sonny Styles
6 Francis Mauigoa
7 Carnell Tate
8 Caleb Downs
9 Rueben Bain
10 Mansoor Delane
11 Spencer Fano
12 Makai Lemon
14 Jordyn Tyson
15 Jermod McCoy
16 Olaivavega Ioane
17 Kenyon Sadiq
18 Dillon Thieneman
19 Kadyn Proctor
20 Keldric Faulk
21 Akheem Mesidor
22 Omar Cooper Jr.
23 Emmanuel McNeil-Warren
24 Kevin Coleman Jr.
25 Blake Miller
26 Caleb Lomu
28 Peter Woods
29 T.J. Parker
30 Max Iheanachor
31 Kayden McDonald
32 Avieon Terrell
33 Ty Simpson
34 Colton Hood
35 Cashius Howell
36 C.J. Allen
37 Zion Young
38 Chris Johnson
39 Malachi Lawrence
40 Caleb Banks
41 Chase Bisontis
42 Emmanuel Pregnon
43 Jadarian Price
44 Brandon Cisse
45 Jacob Rodriguez
46 R. Mason Thomas
47 Christen Miller
48 Anthony Hill Jr.
49 Eli Stowers
50 Lee Hunter
51 D'Angelo Ponds
52 Chris Brazzell II
53 Chris Bell
54 Gabe Jacas
55 Keylan Rutledge
56 Germie Bernard
57 Treydan Stukes
58 Jake Golday
59 Mike Washington Jr.
60 A.J. Haulcy
61 Derrick Moore
62 Gennings Dunker
63 Carson Beck
64 Keionte Scott
65 Josiah Trotter
66 Connor Lew
67 Zachariah Branch
68 Caleb Tiernan
69 Dominique Orange
70 Keith Abney II
71 Max Klare
72 Dani Dennis-Sutton
73 Ted Hurst
74 Skyler Bell
75 Antonio Williams
76 Elijah Sarratt
77 Malachi Fields
78 Kyle Louis
79 Gracen Halton
80 Romello Height
81 Davison Igbinosun
82 Joshua Josephs
83 Garrett Nussmeier
84 Sam Hecht
85 Oscar Delp
86 Keyron Crawford
87 Jaishawn Barham
88 Malik Muhammad
89 Bud Clark
90 Bryce Lance
91 Jalon Kilgore
92 Jonah Coleman
93 Darrell Jackson Jr.
94 Zakee Wheatley
95 Kamari Ramsey
96 De'Zhaun Stribling
97 Julian Neal
98 Devin Moore
99 Drew Allar
100 Logan Jones
101 Dametrious Crownover
102 Markel Bell
103 Chandler Rivers
104 Daylen Everette
105 Deion Burks
106 Jalen Farmer
107 Jake Slaughter
108 Genesis Smith
109 Ja'Kobi Lane
110 Brenen Thompson
111 Sam Roush
112 Justin Joly
113 L.T. Overton
114 Emmett Johnson
115 Zxavian Harris
116 Brian Parker II
117 Austin Barber
118 Deontae Lawson
119 Kaleb Proctor
120 Michael Trigg
121 VJ Payne
122 Trey Zuhn III
123 Chris McClellan
124 Tyler Onyedim
125 Kaleb Elarms-Orr
126 Tacario Davis
127 Will Lee III
128 Kage Casey
129 Jude Bowry
130 Cole Payton
131 Keyshaun Elliott
132 Billy Schrauth
133 Eli Raridon
134 Anthony Lucas
135 Harold Perkins
136 Rayshaun Benny
137 Travis Burke
138 Taylen Green
139 Zane Durant
140 Ephesians Prysock
141 Dontay Corleone
142 Kaytron Allen
143 Nick Singleton
144 Beau Stephens
145 Caden Curry
146 Max Llewellyn
147 DeMonte Capehart
148 Bryce Boettcher
149 Jack Endries
150 Isaiah World
151 Tim Keenan III
152 Hezekiah Masses
153 Josh Cameron
154 Michael Taaffe
155 Jimmy Rolder
156 Aiden Fisher
157 Jadon Canady
158 Jeff Caldwell
159 Taurean York
160 Charles Demmings
161 J.C. Davis
162 Drew Shelton
163 Joe Royer
164 Keagen Trost
165 Nick Barrett
166 Jeremiah Wright
167 Jakobe Thomas
168 Marlin Klein
169 Demond Claiborne
170 Nate Boerkircher
171 Adam Randall
172 Jack Kelly
173 Jager Burton
174 Cade Klubnik
175 Albert Regis
176 Kevin Coleman Jr.
178 Parker Brailsford
179 TJ Hall
180 Nadame Tucker
181 Matt Gulbin
182 Anez Cooper
183 Justin Jefferson
184 George Gumbs Jr.
185 Tanner Koziol
186 Dallen Bentley
187 Kendrick Law
188 Red Murdock
189 Mason Reiger
190 Domani Jackson
191 Febechi Nwaiwu
192 Reggie Virgil
193 Wesley Williams
194 Ar'maj Reed-Adams
195 Landon Robinson
196 Tyreak Sapp
197 Kaelon Black
198 Jalen Huskey
199 Pat Coogan
200 Cyrus Allen
201 Louis Moore
202 Le'Veon Moss
203 Robert Spears-Jennings
204 Will Kacmarek
205 Carver Willis
206 J'Mari Taylor
207 Bishop Fitzgerald
208 Thaddeus Dixon
209 Riley Nowakowski
210 Aamil Wagner
211 Trey Moore
212 Seth McGowan
213 Kaden Wetjen
214 Eli Heidenreich
215 Devon Marshall
216 Mikail Kamara
217 Dalton Johnson
218 Caleb Douglas
219 Matthew Hibner
220 Jaydn Ott
221 Josh Cuevas
222 Rene Konga
223 Lorenzo Styles Jr.
224 Lander Barton
225 Malik Benson
226 Andre Fuller
227 Vincent Anthony Jr.
228 Cole Wisniewski
229 Logan Fano
230 Collin Wright
231 Logan Taylor
232 Quintayvious Hutchins
233 Caden Barnett
234 Colbie Young
235 John Michael Gyllenborg
236 D.J. Campbell
237 Skyler Gill-Howard
238 Roman Hemby
239 Jordan van den Berg
240 Eric Gentry
241 Brandon Cleveland
242 C.J. Daniels
243 Kendal Daniels
244 Alex Harkey
245 J.Michael Sturdivant
246 David Gusta
247 Bryson Eason
248 Cameron Ball
249 Dae'Quan Wright
250 Barion Brown
251 Nolan Rucci
252 Tyren Montgomery
253 Owen Heinecke
254 Zavion Thomas
255 Toriano Pride
256 Haynes King
257 Joe Fagnano
258 Fernando Carmona
259 Latrell McCutchin
260 Sawyer Robertson
261 Jamarion Miller
262 Avery Smith
263 DeShon Singleton
264 Michael Heldman
265 Enrique Cruz Jr.
266 Noah Whittington
267 Eric Rivers
268 Micah Morris
269 Eric McAlister
270 Xavier Nwankpa
271 Deven Eastern
272 Luke Altmyer
273 Karson Sharar
274 Aaron Graves
275 Brett Thorson
276 Jack Pyburn
277 Jaden Dugger
278 Evan Beerntsen
279 Alan Herron
280 Harrison Wallace III
281 Ahmari Harvey
282 Jeremiah Williams
283 Jaeden Roberts
284 Wade Woodaz
285 Max Bredeson
286 Xavian Sorey Jr.
287 Micah Pettus
288 Ethan Burke
289 Aidan Hubbard
290 Chase Roberts
291 Jalen Stroman
292 Ceyair Wright
293 Lewis Bond
294 Fa'alili Fa'amoe
295 Cole Brevard
296 Robert Henry Jr.
297 Jalon Daniels
298 Diego Pavia
299 DJ Rogers
300 Patrick Payton
301 Emmanuel Henderson
302 Lake McRee
303 Trey Smack
304 Nyjalik Kelly
305 Jordan Hudson
306 Chip Trayanum
307 Desmond Reid
308 Kobe Baynes
309 Gary Smith III
310 Marcus Allen
311 Josh Moten
312 Aaron Anderson
313 Keyshawn James-Newby
314 Bauer Sharp
315 Wesley Bissainthe
316 Rahsul Faison
317 Carsen Ryan
318 James Thompson Jr.
319 Behren Morton
320 Dillon Bell
321 Namdi Obiazor
322 James Brockermeyer
323 Bryan Thomas Jr.
324 Jackson Kuwatch
325 Zach Durfee
326 Anterio Thompson
327 Tyre West
328 Wydett Williams Jr.
329 Garrett DiGiorgio
330 Austin Brown
331 Uar Bernard
332 Dean Connors
333 Vinny Anthony II
334 Joshua Braun
335 Shadrach Banks
336 C.J. Donaldson
337 Kolbey Taylor
"""

def _norm(s):
    if not isinstance(s, str): return ""
    return (s.strip().lower()
            .replace(".", "").replace("'", "").replace("-", " ").replace(",","")
            .replace(" jr", "").replace(" ii", "").replace(" iii", ""))

# Parse consensus
consensus = {}
for line in CONSENSUS_4_20.strip().split("\n"):
    parts = line.strip().split(None, 1)
    if len(parts) != 2: continue
    rank = int(parts[0])
    name = parts[1].strip()
    consensus[_norm(name)] = (rank, name)

print(f"Parsed {len(consensus)} consensus-ranked prospects")

# Load prospects
p = pd.read_csv(PROS)
p["_nk"] = p["player"].map(_norm)

# Also try surname-only matching for collision-prone names
updated = 0
unmatched = []
# Build lookup
rank_map = {k: v[0] for k, v in consensus.items()}

# Direct full-name match
p["rank_new"] = p["_nk"].map(rank_map)
matched_full = p["rank_new"].notna().sum()

# Also try alternative name normalizations (e.g. KC vs Kevin for Concepcion)
alias_map = {
    _norm("Kevin Coleman Jr."):   24,   # ambiguous — appears 2x in list
    _norm("K.C. Concepcion"):     24,   # NFLMDD lists him as "Kevin"
    _norm("KC Concepcion"):       24,
    _norm("R. Mason Thomas"):     46,
    _norm("R Mason Thomas"):      46,
    _norm("D'Angelo Ponds"):      51,
    _norm("D'angelo Ponds"):      51,
}
for nk, r in alias_map.items():
    if nk in p["_nk"].values and pd.isna(p.loc[p["_nk"]==nk, "rank_new"]).all():
        p.loc[p["_nk"]==nk, "rank_new"] = r

# Apply updates — overwrite `rank` column
p["rank"] = p["rank_new"]
updated = p["rank"].notna().sum()
p = p.drop(columns=["_nk", "rank_new"])
p.to_csv(PROS, index=False)

print(f"Matched and updated rank for {updated} prospects")
# Print a few unmatched top-100 for visibility
cons_norm_set = set(consensus.keys())
unmatched_cons_top100 = [name for nk, (r, name) in consensus.items()
                         if r <= 100 and nk not in p["player"].map(_norm).values]
if unmatched_cons_top100:
    print(f"Consensus top-100 names NOT found in prospects CSV: {unmatched_cons_top100[:15]}")
