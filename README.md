# Elder Scrolls Dark Brotherhood Trivia

![Deploy](https://github.com/mastash3ff/Alexa-ElderScrollsDBTrivia/actions/workflows/deploy.yml/badge.svg)

An Alexa trivia game covering the Dark Brotherhood questline across the Elder Scrolls series. Answer 5 multiple-choice questions drawn randomly from a bank of 22.

## Usage

**Invocation:** `dark brotherhood trivia`

| Say... | Response |
|--------|----------|
| "Alexa, open dark brotherhood trivia" | Starts a new 5-question game |
| "One" / "Two" / "Three" / "Four" | Submits your answer for the current question |
| "I don't know" | Reveals the answer and moves on |
| "Repeat" | Re-reads the current question |
| "Start over" | Restarts the game with new questions |
| "Help" | Explains how to play |
| "Stop" / "Exit" | Ends the skill |

## How to play

Alexa reads a question and four numbered choices. Say the number of your answer. After all 5 questions your final score is announced.

## Development

**Stack:** Python 3.12 · ASK SDK v2 · AWS Lambda (us-east-1)

```bash
# Install dependencies
pip install -r src/requirements.txt

# Run tests
PYTHONPATH=src pytest tests/ -v

# Deploy — automatic on push to master via GitHub Actions
```

## Project structure

```
src/lambda_function.py      Intent handlers and game logic
src/data.py                 Question bank (22 questions, 4 choices each)
src/requirements.txt        ask-sdk-core dependency
tests/test_skill.py         Unit tests
.github/workflows/          CI/CD — tests gate deployment to Lambda
```
