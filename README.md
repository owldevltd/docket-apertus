# Docket

Hack Apertus 2026 · Track 2A (OpenParlData) · built on [Apertus](https://huggingface.co/swiss-ai)

Docket turns the PDF of a Swiss parliamentary document – born digital or scanned, German, French or Italian – into
one structured affair record, and every value in it carries the place on the page it came from. What the model
guesses is marked for a person; what a person corrects becomes a rule.

```
cd track_2a
cp .env.example .env    # put your key after LLM_API_KEY=
make run                # Docker; then open http://localhost:8080/en/
```

What you need, how to try it with a first PDF, the results and the tests: [`track_2a/README.md`](track_2a/README.md).
The technical report is [`track_2a/technical_report.md`](track_2a/technical_report.md). Licensed under Apache 2.0, see
[LICENSE](LICENSE).
