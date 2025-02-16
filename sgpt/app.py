# To allow users to use arrow keys in the REPL.
import readline  # noqa: F401
import sys

import typer
from click import BadArgumentUsage, MissingParameter
from click.types import Choice

from sgpt.config import cfg
from sgpt.handlers.chat_handler import ChatHandler
from sgpt.handlers.default_handler import DefaultHandler
from sgpt.handlers.repl_handler import ReplHandler
from sgpt.role import DefaultRoles, SystemRole
from sgpt.utils import get_edited_prompt, install_shell_integration, run_command, copy_to_clipboard



def main(
    prompt: str = typer.Argument(
        None,
        show_default=False,
        help="The prompt to generate completions for.",
    ),
    model: str = typer.Option(
        cfg.get("DEFAULT_MODEL"),
        help="Large language model to use.",
    ),
    temperature: float = typer.Option(
        0.1,
        min=0.0,
        max=2.0,
        help="Randomness of generated output.",
    ),
    top_probability: float = typer.Option(
        1.0,
        min=0.1,
        max=1.0,
        help="Limits highest probable tokens (words).",
    ),
    shell: bool = typer.Option(
        False,
        "--shell",
        "-s",
        help="Generate and execute shell commands.",
        rich_help_panel="Assistance Options",
    ),
    describe_shell: bool = typer.Option(
        False,
        "--describe-shell",
        "--ds",
        help="Describe a shell command.",
        rich_help_panel="Assistance Options",
    ),
    code: bool = typer.Option(
        False,
        "--code",
        "-c",
        help="Generate only code.",
        rich_help_panel="Assistance Options",
    ),
    editor: bool = typer.Option(
        False,
        "--editor",
        "-e",
        help="Open $EDITOR to provide a prompt.",
    ),
    cache: bool = typer.Option(
        True,
        help="Cache completion results.",
    ),
    chat_id: str = typer.Option(
        "temp",
        "--chat-id",
        "--id",
        help="Follow conversation with id, default id 'temp' is always cleaned up on new sgpt execution.",
        rich_help_panel="Chat Options",
    ),
    repl: bool = typer.Option(
        False,
        "--interactive",
        "-i",
        help="Start a REPL (Read–eval–print loop) session within chat id --chat-id/--id.",
        rich_help_panel="Chat Options",
    ),
    print_chat: bool = typer.Option(
        False,
        "--print-chat",
        "-p",
        help="Show all messages from provided chat id --chat-id/--id.",
        rich_help_panel="Chat Options",
    ),
    delete_chat: bool = typer.Option(
        False,
        "--delete-chat",
        "-d",
        help="Delete all messages from provided chat id --chat-id/--id.",
        rich_help_panel="Chat Options",
    ),
    list_chats: bool = typer.Option(
        False,
        "--list-chats",
        "-l",
        help="List all existing chat ids.",
        callback=ChatHandler.list_ids,
        rich_help_panel="Chat Options",
    ),
    role: str = typer.Option(
        None,
        "--role",
        "-r",
        help="System role for GPT model.",
        rich_help_panel="Role Options",
    ),
    create_role: str = typer.Option(
        None,
        "--create-role",
        "--cr",
        help="Create role.",
        callback=SystemRole.create,
        rich_help_panel="Role Options",
    ),
    show_role: str = typer.Option(
        None,
        "--show-role",
        "--sr",
        help="Show role.",
        callback=SystemRole.show,
        rich_help_panel="Role Options",
    ),
    list_roles: bool = typer.Option(
        False,
        "--list-roles",
        "--lr",
        help="List roles.",
        callback=SystemRole.list,
        rich_help_panel="Role Options",
    ),
    install_integration: bool = typer.Option(
        False,
        help="Install shell integration (ZSH and Bash only)",
        callback=install_shell_integration,
        hidden=True,  # Hiding since should be used only once.
    ),
) -> None:
    stdin_passed = not sys.stdin.isatty()

    if stdin_passed and not repl:
        prompt = f"{sys.stdin.read()}\n\n{prompt or ''}"


    if sum((shell, describe_shell, code)) > 1:
        raise BadArgumentUsage(
            "Only one of --shell, --describe-shell, and --code options can be used at a time."
        )

    if editor and stdin_passed:
        raise BadArgumentUsage("--editor option cannot be used with stdin input.")

    if editor:
        prompt = get_edited_prompt()

    role_class = (
        DefaultRoles.check_get(shell, describe_shell, code)
        if not role
        else SystemRole.get(role)
    )

    if repl:
        # Will be in infinite loop here until user exits with Ctrl+C.
        ReplHandler(chat_id, role_class).handle(
            prompt,
            model=model,
            temperature=temperature,
            top_probability=top_probability,
            chat_id=chat_id,
            caching=cache,
        )

    if print_chat:
        ChatHandler.show_messages_callback(chat_id)
        exit()

    if delete_chat:
        ChatHandler(chat_id, role_class).delete_chat(chat_id)
        exit()

    if chat_id:
        if not prompt:
            raise MissingParameter(param_hint="PROMPT", param_type="string")
        full_completion = ChatHandler(chat_id, role_class).handle(
            prompt,
            model=model,
            temperature=temperature,
            top_probability=top_probability,
            chat_id=chat_id,
            caching=cache,
        )


    if code:
        option = typer.prompt(
            text="[C]opy, [A]bort",
            type=Choice(("c", "a"), case_sensitive=False),
            default="a" ,
            show_choices=False,
            show_default=False,
        )
        if option in ("c"):
            copy_to_clipboard(full_completion)
            print("Command copied to clipboard!")

    while shell and not stdin_passed:
        option = typer.prompt(
            text="[E]xecute, [C]opy, [D]escribe, [A]bort",
            type=Choice(("e", "d", "a", "y", "c"), case_sensitive=False),
            default="e" if cfg.get("DEFAULT_EXECUTE_SHELL_CMD") == "true" else "a",
            show_choices=False,
            show_default=False,
        )
        if option in ("e", "y"):
            # "y" option is for keeping compatibility with old version.
            run_command(full_completion)
        if option in ("c"):
            copy_to_clipboard(full_completion)
            print("Command copied to clipboard!")
        elif option == "d":
            DefaultHandler(DefaultRoles.DESCRIBE_SHELL.get_role()).handle(
                full_completion,
                model=model,
                temperature=temperature,
                top_probability=top_probability,
                caching=cache,
            )
            continue
        break


def entry_point() -> None:
    # Python package entry point defined in setup.py
    typer.run(main)


if __name__ == "__main__":
    entry_point()
