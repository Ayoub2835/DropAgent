# Royalty-free music library

DropAgent does **not** bundle any third-party music to avoid copyright
issues. Drop your own royalty-free tracks into this folder and tag them in
`manifest.json` so `MusicLibrary` can pick one that matches a story's
genre/mood.

## Where to get legally safe tracks

- [YouTube Audio Library](https://www.youtube.com/audiolibrary) - free, some tracks require attribution.
- [Pixabay Music](https://pixabay.com/music/) - free for commercial use, no attribution required.
- [Free Music Archive](https://freemusicarchive.org/) - filter by CC0 / CC-BY license.
- [Incompetech (Kevin MacLeod)](https://incompetech.com/) - free with attribution under CC-BY.
- [Uppbeat](https://uppbeat.io/) - free tier with attribution, paid tier without.

Always double-check the specific license of each track (attribution
requirements, commercial-use permissions) before publishing.

## manifest.json format

```json
{
  "tracks": [
    { "file": "tense_pulse.mp3", "moods": ["horror", "suspense", "thriller"] },
    { "file": "warm_piano.mp3", "moods": ["drama", "romance", "wholesome"] },
    { "file": "epic_rise.mp3", "moods": ["adventure", "motivational", "action"] }
  ]
}
```

- `file`: filename relative to this folder.
- `moods`: lowercase tags matched against the `--genre` passed to DropAgent.

If no `manifest.json` is present, DropAgent will use any audio file dropped
directly in this folder (untagged), and if the folder is empty it will
simply render the video without background music instead of failing.
