# Music Characteristics: Cyanite playlist analyzer

Cyanite analyzes one song at a time. This tool takes the Cyanite results for
every song in a playlist and analyzes the **playlist as a whole**.

## How to use

1. Analyze your playlist's songs on [cyanite.ai](https://cyanite.ai).
2. Export the results to CSV (or copy them into a spreadsheet and save it as
   CSV), one row per song. See `example_playlist.csv` for the layout.
3. Run:

   ```
   python3 playlist_analyzer.py my_playlist.csv
   ```

You get a summary in the terminal and an HTML report
(`my_playlist_report.html`) you can open in a browser.

## What it reports

- **Overall vibe**: the main moods, genres, tempo and energy
- **Mix breakdowns**: genre, subgenre, mood, character, movement, instruments, keys, voice
- **BPM range** and **energy flow** across the current track order
- **Songs that don't fit**: tracks whose tempo, energy, genre or mood stand out, and why
- **Suggested order**: smoother transitions in key (Camelot wheel), BPM and energy

## CSV columns

Column names are matched loosely, so a Cyanite export should work as-is.
Any of these are used when present (others are ignored):

| Field | Example header names | Example values |
|---|---|---|
| Title / Artist | `Title`, `Track`, `File name` / `Artist` | |
| BPM | `BPM`, `Tempo` | `98` |
| Key | `Key` | `A minor`, `C#m`, `aMinor`, `Bb` |
| Energy | `Energy Level`, `Energy` | `Low` … `Very High`, or `0.7` / `70%` |
| Genre, Subgenre, Mood, Character, Movement, Instruments | same names | comma-separated tags, e.g. `Dark, Chilled` |
| Voice | `Voice`, `Vocals` | `Female` |

Only Python 3 is needed; there are no extra packages to install.

## Web version

`web/index.html` is the same analyzer as a web page: upload your CSV in the
browser and the report appears right there. Nothing is uploaded anywhere; the
file is read in your browser.
