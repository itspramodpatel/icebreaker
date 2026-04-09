from __future__ import annotations

import asyncio
import os
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from icebreaker.company_resolver import resolve_company
from icebreaker.company_synthesizer import synthesize_company
from icebreaker.config import Config
from icebreaker.output import brief_to_html, brief_to_markdown, company_brief_to_markdown
from icebreaker.pipeline import run_pipeline
from icebreaker.resolver import resolve
from icebreaker.synthesizer import synthesize


def bootstrap_streamlit_secrets() -> None:
    """Expose Streamlit secrets as environment variables for existing config loading."""
    secret_keys = [
        "ICEBREAKER_ANTHROPIC_API_KEY",
        "ICEBREAKER_SERPAPI_KEY",
        "ICEBREAKER_SEARCHAPI_KEY",
        "ICEBREAKER_GOOGLE_CSE_KEY",
        "ICEBREAKER_GOOGLE_CSE_ID",
        "ICEBREAKER_PROXYCURL_KEY",
        "ICEBREAKER_GITHUB_TOKEN",
    ]
    for key in secret_keys:
        if not os.environ.get(key):
            value = st.secrets.get(key, "")
            if value:
                os.environ[key] = str(value)


bootstrap_streamlit_secrets()

st.set_page_config(
    page_title="Icebreaker",
    layout="wide",
)


def generate_profile(name: str, linkedin_url: str, company: str, location: str):
    config = Config()
    identity = resolve(
        linkedin_url,
        name=name or None,
        company=company or None,
        location=location or None,
    )
    profile = asyncio.run(run_pipeline(identity, config))
    brief = asyncio.run(synthesize(profile, config))
    return brief, profile


def generate_company_brief(
    company_name: str,
    website: str,
    linkedin_company_url: str,
    geography: str,
    industry: str,
    target_roles: list[str],
    event_focus: str,
    services: str,
):
    config = Config()
    identity = resolve_company(
        company_name=company_name,
        website=website or None,
        linkedin_company_url=linkedin_company_url or None,
        geography=geography or None,
        industry=industry or None,
        target_roles=target_roles,
        event_focus=event_focus or None,
        services=services or None,
    )
    profile = asyncio.run(run_pipeline(identity, config))
    brief = asyncio.run(synthesize_company(profile, config))
    return brief, profile


def format_profile_evidence(profile) -> str:
    lines = []
    for collector in profile.collector_results:
        status = "success" if collector.success else f"error: {collector.error or 'unknown'}"
        lines.append(f"## {collector.source} ({status})")
        for result in collector.results[:30]:
            if result.title:
                lines.append(f"Title: {result.title}")
            if result.url:
                lines.append(f"URL: {result.url}")
            if result.snippet:
                lines.append(f"Snippet: {result.snippet}")
            if result.content:
                lines.append(f"Content: {result.content[:800]}")
            lines.append("---")
        lines.append("")
    return "\n".join(lines).strip() or "No evidence collected."


st.title("Icebreaker")
st.caption("Client testing app for generating relationship-intelligence profile HTML from public information.")

with st.sidebar:
    st.subheader("Setup")
    st.write("This app needs `ICEBREAKER_ANTHROPIC_API_KEY` configured in the host environment.")
    st.write("Search quality improves if you also provide SerpAPI, SearchAPI, or Google CSE keys.")
    if "debug_show_config" not in st.session_state:
        st.session_state["debug_show_config"] = False
    st.session_state["debug_show_config"] = st.checkbox(
        "Show config debug",
        value=st.session_state["debug_show_config"],
        help="Safe runtime checks for key presence only. No secret values are shown.",
    )

config_ok = True
config_error = None
try:
    config = Config()
    if not config.has_anthropic():
        config_ok = False
        config_error = "Missing `ICEBREAKER_ANTHROPIC_API_KEY`."
except Exception as exc:
    config_ok = False
    config_error = str(exc)

if not config_ok:
    st.error(config_error or "Configuration error.")

if config_ok and st.session_state.get("debug_show_config"):
    serp_key = getattr(config, "serpapi_key", "") or ""
    searchapi_key = getattr(config, "searchapi_key", "") or ""
    anth_key = getattr(config, "anthropic_api_key", "") or ""
    st.info(
        "\n".join(
            [
                f"Anthropic key loaded: {'yes' if bool(anth_key) else 'no'}",
                f"SerpAPI key loaded: {'yes' if bool(serp_key) else 'no'}",
                f"SerpAPI key length: {len(serp_key)}",
                f"SearchAPI key loaded: {'yes' if bool(searchapi_key) else 'no'}",
                f"SearchAPI key length: {len(searchapi_key)}",
                f"Google CSE configured: {'yes' if config.has_google_cse() else 'no'}",
            ]
        )
    )

people_tab, company_tab = st.tabs(["People Brief", "Company Brief"])

with people_tab:
    col1, col2 = st.columns([1, 1])
    with col1:
        name = st.text_input("Full name", placeholder="Jane Doe")
    with col2:
        linkedin_url = st.text_input(
            "LinkedIn profile URL",
            placeholder="https://www.linkedin.com/in/jane-doe/",
        )

    col3, col4 = st.columns([1, 1])
    with col3:
        company = st.text_input("Company (optional)", placeholder="Acme Corp")
    with col4:
        location = st.text_input("Location (optional)", placeholder="San Francisco")

    run_clicked = st.button("Generate profile HTML", type="primary", disabled=not config_ok)

    if run_clicked:
        if not name.strip():
            st.warning("Enter the person's full name.")
        elif not linkedin_url.strip():
            st.warning("Enter a LinkedIn profile URL.")
        else:
            with st.spinner("Gathering public data and generating the profile..."):
                try:
                    brief, profile = generate_profile(
                        name=name.strip(),
                        linkedin_url=linkedin_url.strip(),
                        company=company.strip(),
                        location=location.strip(),
                    )
                    html = brief_to_html(brief)
                    markdown = brief_to_markdown(brief)
                    file_stem = brief.subject_name.replace(" ", "_").lower()

                    st.session_state["generated_html"] = html
                    st.session_state["generated_markdown"] = markdown
                    st.session_state["generated_name"] = brief.subject_name
                    st.session_state["result_count"] = len(profile.all_results())
                    st.session_state["file_stem"] = file_stem
                    st.session_state["people_evidence"] = format_profile_evidence(profile)
                except Exception as exc:
                    st.exception(exc)

    if "generated_html" in st.session_state:
        st.success(
            f"Generated profile for {st.session_state['generated_name']} from "
            f"{st.session_state['result_count']} collected public data points."
        )

        action_col1, action_col2 = st.columns([1, 1])
        with action_col1:
            st.download_button(
                "Download HTML",
                data=st.session_state["generated_html"],
                file_name=f"{st.session_state['file_stem']}_brief.html",
                mime="text/html",
                use_container_width=True,
            )
        with action_col2:
            st.download_button(
                "Download Markdown",
                data=st.session_state["generated_markdown"],
                file_name=f"{st.session_state['file_stem']}_brief.md",
                mime="text/markdown",
                use_container_width=True,
            )

        with st.expander("Preview HTML", expanded=True):
            components.html(st.session_state["generated_html"], height=900, scrolling=True)

        with st.expander("Generated Markdown"):
            st.code(st.session_state["generated_markdown"], language="markdown")
        if "people_evidence" in st.session_state:
            with st.expander("Collected Raw Evidence"):
                st.code(st.session_state["people_evidence"], language="markdown")

        template_path = Path(__file__).parent / "icebreaker" / "templates" / "profile.html"
        if not template_path.exists():
            st.warning("Template file is missing, so deployment packaging should be checked before sharing.")

with company_tab:
    st.caption("Research target companies, likely buyer roles, event signals, and outreach angles.")

    c1, c2 = st.columns([1, 1])
    with c1:
        company_name = st.text_input("Company name", placeholder="Nike")
    with c2:
        company_site = st.text_input("Company website", placeholder="https://www.nike.com")

    c3, c4 = st.columns([1, 1])
    with c3:
        linkedin_company_url = st.text_input(
            "LinkedIn company URL (optional)",
            placeholder="https://www.linkedin.com/company/nike/",
        )
    with c4:
        geography = st.text_input("Geography / market (optional)", placeholder="Middle East")

    c5, c6 = st.columns([1, 1])
    with c5:
        industry = st.text_input("Industry (optional)", placeholder="Retail")
    with c6:
        event_focus = st.text_input(
            "Event focus (optional)",
            placeholder="exhibitions, activations, trade shows",
        )

    default_roles = (
        "CMO, Marketing Director, Marketing Manager, Brand Director, "
        "Brand Manager, Event Director, Event Manager"
    )
    target_roles_text = st.text_area("Target roles", value=default_roles, height=100)
    services = st.text_area(
        "Your services / offering (optional)",
        placeholder="Exhibition design, experiential activations, branded environments",
        height=100,
    )

    company_clicked = st.button("Generate company brief", disabled=not config_ok)

    if company_clicked:
        if not company_name.strip():
            st.warning("Enter a company name.")
        else:
            with st.spinner("Researching the company and generating the opportunity brief..."):
                try:
                    target_roles = [
                        role.strip() for role in target_roles_text.split(",") if role.strip()
                    ]
                    brief, profile = generate_company_brief(
                        company_name=company_name.strip(),
                        website=company_site.strip(),
                        linkedin_company_url=linkedin_company_url.strip(),
                        geography=geography.strip(),
                        industry=industry.strip(),
                        target_roles=target_roles,
                        event_focus=event_focus.strip(),
                        services=services.strip(),
                    )
                    markdown = company_brief_to_markdown(brief)
                    file_stem = brief.company_name.replace(" ", "_").lower()

                    st.session_state["company_markdown"] = markdown
                    st.session_state["company_name_generated"] = brief.company_name
                    st.session_state["company_result_count"] = len(profile.all_results())
                    st.session_state["company_file_stem"] = file_stem
                    st.session_state["company_evidence"] = format_profile_evidence(profile)
                except Exception as exc:
                    st.exception(exc)

    if "company_markdown" in st.session_state:
        st.success(
            f"Generated company brief for {st.session_state['company_name_generated']} from "
            f"{st.session_state['company_result_count']} collected public data points."
        )
        st.download_button(
            "Download Company Markdown",
            data=st.session_state["company_markdown"],
            file_name=f"{st.session_state['company_file_stem']}_opportunity_brief.md",
            mime="text/markdown",
            use_container_width=True,
        )
        with st.expander("Company Brief Markdown", expanded=True):
            st.code(st.session_state["company_markdown"], language="markdown")
        if "company_evidence" in st.session_state:
            with st.expander("Collected Raw Evidence"):
                st.code(st.session_state["company_evidence"], language="markdown")
