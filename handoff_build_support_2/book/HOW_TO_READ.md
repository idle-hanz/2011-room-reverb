# How to read this book — start here if you are not an engineer

*For Idle, first. Draft 2026-10-05.*

This book explains how the 2011 Room Reverb works: what you built in 2011, what has been added since, and what is coming. It is written so you never have to take anything on trust, and so that one day someone else (Ben) can pick it up without the chat history.

## The short route (about an hour)

1. **Chapter 2, §2.0** "The whole picture in plain English": one page on how a clap in a room becomes direct sound, early echoes and a tail, and how the program builds each.
2. **Chapter 2, §2.7**: a one-page preview of how Surfaces will shape the sound.
3. **Chapter 5, §5.0 and §5.6a**: the engine as 32 corridors that feed each other, and *why* a filter has to be inside the loop to change how long the tail lasts.
4. **Chapter 6, §6.0**: the bouncing ball and the tuned sponges, then the summary table in §6.5a and the auto-treat explanation in §6.6.

That is enough to understand how Surfaces will shape the sound.

## The full route

Read Chapters 1 to 8 in order. In each chapter, after every dense section, there is a quoted box called **"In plain English"**. If a section loses you, skip to its box, then go back if you want the detail. In Chapter 6 each of the eight steps starts with a **"Plain first"** note before any formula.

## When you meet a word you don't know

Look it up in **`99_glossary.md`**. Every term used in Chapters 1–8 has a one-line everyday meaning, followed by the precise version.

## The four labels and what they promise

| Label | What it means for you |
|---|---|
| **VERIFIED** | Someone measured it or read it in a named file. You can check it. |
| **ASSUMED** | A judgement or something not re-checked. Treat it as a good guess. |
| **LOCKED** | You approved it, but it is not in the program yet. |
| **PLANNED** | An idea or a later design. Nothing is decided in detail. |

You will also see **DESIGNED** (worked out and prototyped on the research machine, not in the program) and **OPEN** (not decided or not known). If a sentence has none of these labels and describes something in the future, that is a mistake in the book: please flag it.

## Five ideas that unlock most of the book

1. **Mirrors for walls.** Each echo is a mirror copy of the instrument behind a wall. Its distance gives its delay and its level.
2. **Corridors that feed each other.** The tail comes from 32 delay lines whose outputs are mixed and sent back round, a little quieter each trip.
3. **Once vs every trip.** A filter before the loop changes tone; a filter inside the loop changes how long each pitch rings.
4. **Bites per bounce.** Each surface swallows a share of the sound at each bounce, differently at each pitch. Tuned panels swallow one bass band.
5. **Nothing changes by accident.** Reference recordings ("goldens") and automatic tests catch any change to the sound that you didn't approve.

## What this book is not

It is not the work plan. The order of the Build sessions is in `../NEXT_SESSION_PLAN.md`, and the book follows it. The book is also never ahead of the code: a chapter is updated only after a session has landed and been checked.
