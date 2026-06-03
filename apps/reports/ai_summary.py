"""Generate an AI-written narrative summary of a Talk queryset via the Anthropic API."""
import os

from django.conf import settings

from .exporters import _rows


def _format_talks(qs) -> str:
    parts = []
    for r in _rows(qs):
        speaker = f"{r['speaker_first_name']} {r['speaker_last_name']}".strip()
        if not speaker:
            speaker = r['assigned_to'] or 'Unknown'
        conference = r['conference_title'] or '(no conference)'
        conf_dates = ''
        if r['conference_start']:
            conf_dates = f" ({r['conference_start']}"
            if r['conference_end']:
                conf_dates += f" – {r['conference_end']}"
            conf_dates += ')'
        flags = []
        if r['plenary'] == 'yes':
            flags.append('PLENARY')
        if r['parallel'] == 'yes':
            flags.append('PARALLEL')
        if r['final_approval'] == 'yes':
            flags.append('APPROVED')
        if r['complete_given'] == 'yes':
            flags.append('GIVEN')
        flag_str = f'  [{", ".join(flags)}]' if flags else ''
        pres_date = r['presentation_date'] or ''
        docdb = r['docdb_number'] or '-'
        line = (
            f"- [{r['status']}] {r['talk_title']}{flag_str}\n"
            f"  Speaker: {speaker}  |  Conference: {conference}{conf_dates}\n"
            f"  Assigned: {r['assigned_to'] or 'Unassigned'}  |  Type: {r['type']}  |  DocDB: {docdb}"
        )
        if pres_date:
            line += f'  |  Date: {pres_date}'
        if r['comments']:
            line += f"\n  {r['comments']}"
        parts.append(line)
    return '\n'.join(parts) if parts else '(no talks)'


def generate(qs, query: str = '', user=None) -> str:
    """Call the Anthropic API and return the summary as a Markdown string."""
    import anthropic
    from .models import AIPromptConfig, DEFAULT_QUERY

    api_key = getattr(settings, 'ANTHROPIC_API_KEY', '') or os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        raise ValueError(
            'ANTHROPIC_API_KEY is not configured. '
            'Set it as an environment variable or in Django settings.'
        )

    config = AIPromptConfig.for_user(user) if user is not None else AIPromptConfig.get_solo()
    model = getattr(settings, 'ANTHROPIC_SUMMARY_MODEL', 'claude-sonnet-4-6')
    base_url = getattr(settings, 'ANTHROPIC_BASE_URL', '') or None
    client = anthropic.Anthropic(api_key=api_key, **({"base_url": base_url} if base_url else {}))

    talks_text = _format_talks(qs)
    effective_query = query.strip() or DEFAULT_QUERY

    try:
        content = config.user_template.format(talks=talks_text, query=effective_query)
    except KeyError:
        content = config.user_template.format(talks=talks_text)

    message = client.messages.create(
        model=model,
        max_tokens=4096,
        system=config.system_prompt,
        messages=[{'role': 'user', 'content': content}],
    )
    return message.content[0].text
