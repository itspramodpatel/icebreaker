# Icebreaker Hosting

## Best quick option

Use Streamlit Community Cloud for client testing.

## What I already added

- `app.py` - Streamlit frontend for name + LinkedIn URL input
- `requirements.txt` - dependencies for Community Cloud
- `.streamlit/secrets.toml.example` - copy/paste template for Streamlit secrets

## Local run

```bash
cd /Users/pramodpatel/Desktop/icebreaker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Required environment variables

- `ICEBREAKER_ANTHROPIC_API_KEY`

## Optional environment variables

- `ICEBREAKER_SERPAPI_KEY`
- `ICEBREAKER_GOOGLE_CSE_KEY`
- `ICEBREAKER_GOOGLE_CSE_ID`

## Deploy on Streamlit Community Cloud

1. Put this project in a GitHub repository.
2. In Streamlit Community Cloud, create a new app from that repo.
3. Set the main file path to `app.py`.
4. Open `.streamlit/secrets.toml.example`, copy its contents, and paste them into the app's "Advanced settings" secrets box.
5. Deploy and share the generated URL with the client.

## Notes

- The app asks for a full name and LinkedIn URL, then generates downloadable HTML.
- Search quality is better when you also configure SerpAPI or Google CSE.
- The generated HTML is self-contained and can be downloaded directly from the app.
- Streamlit's docs say Community Cloud supports secrets by pasting your `secrets.toml` contents into the deployed app settings.
