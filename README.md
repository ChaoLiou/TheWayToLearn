# The Way To Learn - PACER Learn

**English** · [繁體中文](docs/README.zh-TW.md)

**This is a [Claude Code](https://claude.com/claude-code) plugin.** Once installed, hand it the link to a YouTube video (or a blog post) and it turns the content into something you can actually read, review, and listen to.

You use it by typing one line in Claude Code (`/pacer:learn <url>`). No programming required. Never used Claude Code before? [Getting started](#getting-started) below walks you through it from the install.

Why you'd want it: you watch an hour-long video called "Why Sleep Matters", nodding along the whole way — and the next day all that's left is "uh, sleep is important."

PACER Learn turns that hour into something that stays with you.

## What you get

| You get a… | Which is really… | Good for |
| --- | --- | --- |
| 📄 **Written explainer** | A web page. How the speaker reasons their way to each conclusion, what every section says, screenshots of the moments that matter, unfamiliar terms explained right where they appear | Going back over a video you watched — or skipping the video entirely |
| 🎧 **Audio version** | An mp3. A spoken walkthrough, cut with clips of the speaker's own voice, with chapters and captions | Commuting, walking, doing the dishes |
| ✍️ **Practice** | A web page. Every piece of information in the video turned into something to *do*: run through the steps, come up with your own example, draw the concept map, drill the flashcard | Actually remembering it, instead of having "seen it" |
| 📝 **Notes** | A web page. 3–8 one-line takeaways per video — the things you only know after watching. Click one to jump back to the part that said it; keep or delete each one yourself | Keeping just the conclusions, or moving them into your own note app |
| 🗂 **Index of every video** | A web page. One card per video you've studied, searchable, showing which one leads into which | Three months later, finding "that video about fixing jet lag" |

All of it is plain web pages stored on your own computer. They work offline, and one command publishes them online so you can read and listen on your phone.

---

## How this differs from "AI, summarize this for me"

**1. It doesn't just list the key points.**
A summary hands you bullet points — but have you ever wondered how the speaker got there? PACER Learn follows the original order, section by section, and tells you, from your seat in the audience, how each one connects to the next. Section 3 raises a question ("so why do some people sleep eight hours and still feel wrecked?") and section 4 picks that question up and answers it. Terms you've never heard get explained on the spot. It reads like a friend sitting next to you, watching the same talk.

**2. Any line takes you back to that second of the video.**
Every section is stamped with a timecode and paired with a screenshot from that moment. If something reads oddly, one click takes you back to hear exactly how they said it.

**3. Watching isn't learning, so it makes you do something.**
Seeing or hearing an idea only gets it in the door. To keep it, you have to digest it — and knowledge comes in types, each digested a different way. Use the wrong method and no amount of time will make it stick.

That's where the name comes from. The method is the PACER framework from *How to Remember Everything You Read*: sort every piece of information into one of five types, then digest it the way that type calls for. PACER is the five initials.

Take a video about sleep:

| Type | What it is | Example from the video | How you digest it |
| --- | --- | --- | --- |
| **P**rocedural | A method, a sequence of steps | Take a hot bath 90 minutes before bed | Do it once, tonight |
| **A**nalogous | "It's just like…" | Caffeine is like taping over the "I'm sleepy" signal | Work out where it holds, where it breaks, when it misleads |
| **C**onceptual | A set of ideas that relate to each other | How body clock, deep sleep and light exposure affect one another | Draw the map yourself, then check it against the answer |
| **E**vidence | The example or number backing a concept | That study where two hours less sleep slowed reactions as much as being tipsy | A day later, explain it without looking |
| **R**eference | Facts and figures you simply memorize | A sleep cycle runs about 90 minutes | Flashcard it, reviewed on a schedule |

The sorting, and what to do with each item, is written for you. You just do it. It remembers what you've done and reminds you when something's due for review.

It also keeps score: if too much piles up undigested (20 items by default), the next time you paste a new video it stops you and tells you to clear the backlog first.

**4. It reads it aloud, with the speaker's own voice mixed in.**
A summary is something you read. This becomes an mp3: a spoken walkthrough that cuts to the speaker's original audio at the moments that matter, like listening to a podcast episode. Chapters to skip between, line-by-line captions on screen, and it works while you walk, drive or wash up. If the original is in another language, those clips can be dubbed instead.

**5. It leaves you a set of notes you curated yourself.**
A summary gets closed and forgotten. Here, each video yields 3–8 one-line takeaways; you keep or delete each one, and what you delete stays gone. Everything you keep links back to the part of the video that said it, and the whole set exports into your own note app.

---

## Getting started

You need a computer (Mac, Windows or Linux) and Claude Code. About 10 minutes.

### 1. Install Claude Code

Follow the [official install guide](https://claude.com/claude-code). You're done when typing `claude` in a terminal gets you in.

### 2. Install two small tools

Copy and paste into your terminal:

**Mac**

```bash
brew install uv ffmpeg
```

**Ubuntu / WSL**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
sudo apt install ffmpeg
```

**Windows (PowerShell)**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
winget install Gyan.FFmpeg
```

(`uv` installs everything the programs need; `ffmpeg` grabs the screenshots out of the video.)

### 3. Install the plugin

Open `claude` and type these two lines:

```
/plugin marketplace add https://github.com/ChaoLiou/TheWayToLearn
/plugin install pacer@thewaytolearn
```

### 4. Paste a link

```
/pacer:learn https://youtu.be/the-one-you-want
```

It **tells you up front** roughly how long it will take, how much of your quota it will use and how much disk it needs, and waits for your go-ahead. A 30-minute video takes about 10–20 minutes, and you can go do something else meanwhile.

The results land in `workspace/` inside whatever folder you're in. Open `plan.html` in a browser to read it.

### 5. (Suggested) One folder per topic

Everything is saved under the folder you were in when you ran the command, so you can organize it however you like.

The nicest way is **one folder per topic**: starting on sleep today? Make a `sleep/` folder, run `/pacer:learn` inside it, and everything sleep-related lands there. Moving on to cooking next month? New folder.

```
my-learning/
├── sleep/      ← run the commands in here, sleep videos land here
└── cooking/    ← new topic, new folder
```

Why bother: each folder gets its own index of videos and its own practice list, so sleep and cooking never get mixed together, and a whole topic is easy to back up or hand to someone. Not bothering is fine too — one folder for everything works just as well.

---

## Things you'll actually type

Say it to Claude Code in whatever language you prefer:

| What you want | Type this |
| --- | --- |
| Study a video (the whole thing) | `/pacer:learn <url>` |
| Just find out what it'll cost first | `/pacer:learn-estimate <url>` |
| What should I review today? | `/pacer:learn-digest today` |
| Walk me through the practice | `/pacer:learn-digest do` |
| Make the audio version | `/pacer:learn-narrate` |
| Pull out the notes | `/pacer:learn-notes` |
| Publish it online (to read on my phone) | `/pacer:learn-publish` |

Whole playlists work too — it asks how many you want and does them one at a time. Blog post URLs work the same way.

---

## A few things you can adjust

It asks once before each run, or you can pass them on the command:

- **Screenshots** `--shots auto|none|many` — by default it only grabs frames you need to *see* to follow along. For a talking-head video, `none` is faster.
- **Whether the AI looks at each screenshot** `--vision true|false` — looking helps it understand, but costs more quota. Turn it off to save.
- **Output language** — by default it writes in whatever language you gave the command in, and the web pages follow suit. To pin it down, say "always use English", or run
  `uv run scripts/options.py learn --save output_lang=en` yourself (stored in that folder's `settings.json`, so `sleep/` can stay Chinese while `cooking/` is English). English and Traditional Chinese interfaces ship today.

---

## FAQ

**Does it cost money?**
It uses your Claude Code quota (depends on video length — figure tens of minutes' worth per video). The speech synthesis is a free service, no extra charge.

**Does it download videos onto my machine?**
Only temporarily, when it needs screenshots, and it deletes them afterwards. With `--shots none` it downloads nothing.

**Where is all my stuff kept?**
Under `workspace/` in the folder you ran the command from, one folder per video, all ordinary HTML and mp3 files. Move them, back them up, drop them into Obsidian — `/pacer:learn-digest` even generates an Obsidian vault for you.

**Do I have to open Claude Code every time?**
No. `/pacer:learn-publish` packages everything for deployment to Cloudflare Pages, after which you just read and listen in your phone's browser.

**What if I don't like what it produced?**
Any stage can be re-run on its own, no starting over: bad section breaks, `/pacer:learn-segment`; weak explanations, `/pacer:learn-analyze`. To change how it writes, the rules in `rules/` are written in plain prose — edit the text and the behavior changes. No code involved.

---

## Want to know how it works underneath

→ [How it works (technical, in Chinese)](docs/how-it-works.zh-TW.md): the full pipeline, who does what at each stage, the engineering trade-offs, how to run each stage on its own, and how to change the rules.
