"""Entry point for the fortigate-8-0-0-copilot application."""

from fortigate_8_0_0_copilot.config import settings


def main() -> None:
    print("Hello from fortigate-8-0-0-copilot!")
    print(f"(environment={settings.app_env}, log_level={settings.log_level})")



"""Only start the program if this file is being used as the program's entry point."""
if __name__ == "__main__":
    main()