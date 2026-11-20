"""Fake tools for the toy agent. nothing real happens: they only describe what would be done."""

TOOLS = {
    "read_file": "read_file(path): read a file and return its text.",
    "search": "search(query): search the company wiki and return results.",
    "send_email": "send_email(to, body): send an email to the given address.",
    "delete_file": "delete_file(path): permanently delete a file.",
    "respond": "respond(message): reply to the user in text without using any other tool.",
}


def execute(tool, args):
    """pretend to run a tool. returns a stub string, never touches the real system."""
    if tool not in TOOLS:
        return f"[error] unknown tool: {tool}"
    return f"[stub] {tool} called with {args}"
