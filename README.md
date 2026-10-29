# Chess Improvement Lab

Replaces the Music Characteristics web page with completed-game chess review. Import PGN (up to 20 games / 2 MB), Lichess public games, or recent Chess.com archives. Select your exact player name or a fixed color. No games have been analyzed for you until you import them. The labeled demo is never personal evidence.

## Run

Node 22+: `npm ci`, `npm test`, `npm run build`, `npm run dev`. Open the served page, not a file:// URL. `dist/` is the website. All analysis uses the locally served Stockfish 18 lite single-threaded worker (depth 10/14); no analysis service receives PGNs. Account import makes requests to the selected platform. Platform failures show errors and PGN remains available.

Engine comparisons evaluate the position before and after each selected-player move with consistent depth. Scores are oriented to the player; at least 100cp loss creates a review candidate. Mate scores are separate transitions, not actual centipawn values. Thresholds, phase labels and coaching categories are app heuristics. Checks/captures in engine leading moves support broad forcing-move labels; this does not prove a fork, pin, hanging piece, opening-theory error or clock-management diagnosis.

Findings show real positions, actual moves, engine alternatives, opponent replies and short practice habits. Candidate-move drills accept legal moves and distinguish the engine's first move without falsely marking every alternative wrong. A single game is not called a recurring weakness. Review batches stay separate with dates/depth for comparison; history exports as JSON. Only completed standard chess is supported. Automatic imports are bounded to 20 games (Chess.com: last three available archive months).

## Deployment and naming

The page title and product branding are Chess Improvement Lab. The GitHub repository remains `Music-Characteristics` so its source identity/old URLs are retained. The new Pages workflow validates PRs without deployment; pushes to the existing default branch deploy `dist/` when GitHub Pages is configured for Actions. No repository rename or hosting-settings mutation is attempted.

The original Python music tool and CSV are preserved in `legacy/`; prior web content remains in Git history. Chess storage uses its own `chessImprovementLab.v1` key. Unreadable or future data is not automatically overwritten. User-initiated Clear only removes this chess key.

## Dependencies and source

- chess.js 1.4.0 (BSD-2-Clause): https://github.com/jhlywa/chess.js
- Stockfish.js 18.0.8 / Stockfish 18 (GPL-3.0): https://github.com/nmrugg/stockfish.js/tree/v18.0.8

Stockfish is an unmodified separately loaded worker. Its license and corresponding source link ship in `dist/engine/`. Lockfile pins packages. No other runtime network dependency is required after page assets load. The lite engine is depth-limited, not an exhaustive proof of best play.

## Explanation-first lessons

Each review candidate is now replayed through chess.js to generate a position-specific lesson: what you played, the legal opponent response, why the line matters, the engine alternative, and a practice habit. Immediate mates are verified as checkmate; material-loss examples count the shown short exchange using conventional piece values, separately from engine evaluation. A blocking explanation is given only when the alternative actually occupies the relevant sliding-piece line. Quiet comparisons explicitly decline unsupported named causes or claims about the player's thoughts.

Main reports display up to three worked examples per pattern immediately; remaining examples stay accessible. Distinct-game counts distinguish a recurring pattern from a single-game observation. Every example has a board walkthrough (before / after your move / reply / alternative) and an optional answer-hidden exercise. New reports retain the next move actually played; historical and engine-only replies are worded differently. Existing saved reviews gain explanations without reanalysis when their stored positions/moves verify. Invalid saved examples decline a diagnosis.
