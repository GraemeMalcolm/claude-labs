---
lab:
  title: Get ready for Claude API development
  description: Create your Claude and Claude Console accounts, and install Visual Studio Code, Git, GitHub, and Python, so you're ready for the Claude labs.
  level: 100
  duration: 20 minutes
  islab: false
---

# Get ready for Claude API development

This exercise should take approximately **20** minutes to complete. It sets up the accounts and tools you'll use in the labs that follow.

> **Note**: The Claude Platform, Claude Code, and the Claude models are subject to continual development. Web pages and menus may change, so some steps may look a little different from these descriptions.

## Create a Claude account

1. In a web browser, open [Claude](https://claude.ai){:target="_blank"} at `https://claude.ai`, and sign up for a Claude account - or sign in if you already have one.

    > **Tip**: A Claude account lets you use Claude in your browser, and it's how you sign in to Claude Code in Visual Studio Code later on.

## Set up an individual Claude Console account

The Claude Console is the web portal where you manage API access, build agents, and create API keys. Use your own individual account for these labs, so that you control your own API keys and usage.

1. In a web browser, go to the [Claude console](https://platform.claude.com){:target="_blank"} at `https://platform.claude.com`, and sign in with your Claude account - or create a Console account if you're prompted to.
1. If prompted, create an organization for your account. Use a name that identifies you personally.
1. Complete any remaining setup steps. The Console uses prepaid credits, and the labs use only a small amount. If your account doesn't have credits, you'll be prompted to add some before you can submit prompts.
1. Confirm that you can open the **API keys** page (under **Settings** in the navigation menu). You'll create API keys in the labs that need them. Treat each key as a secret, and never commit it to source control.

## Install Visual Studio Code

Visual Studio Code is the code editor and terminal you'll use for the labs.

1. In a web browser, go to the [Visual Studio Code page](https://code.visualstudio.com){:target="_blank"} at `https://code.visualstudio.com`, download the installer for your operating system, and run it. The default options are fine.

    > **Tip**: If you're new to Visual Studio Code, the [documentation](https://code.visualstudio.com/docs){:target="_blank"} is a good place to start.

## Create a GitHub account and install Git

You'll clone the lab files from GitHub, and Git is the tool that does the cloning.

1. In a web browser, go to [GitHub](https://github.com){:target="_blank"} at `https://github.com`, and create a free account - or sign in if you already have one.
1. Go to [Git](https://git-scm.com/downloads){:target="_blank"} at `https://git-scm.com/downloads`, download Git for your operating system, and install it. The default options are fine. If you're asked how Git should integrate with Visual Studio Code, choose to use Visual Studio Code as the default editor, or leave the default in place.

## Install Python

The labs use Python to build the client applications. You'll also create a virtual environment for each lab, so you'll need a recent version of Python 3.

1. In a web browser, go to [the Python web site](https://www.python.org/downloads){:target="_blank"} at `https://www.python.org/downloads`, and download the latest Python 3 release (version 3.12 or later).
1. Run the installer. On Windows, select the option to **add Python to PATH** before you install.

## Check your setup

Open a new terminal (in Visual Studio Code, select **Terminal** > **New Terminal**) and check that the tools are available:

1. Run `git --version`. You should see a Git version number.
1. Run `python --version`. You should see a Python 3.12 or later version number.

    > **Tip**: On Windows, if running `python` opens the Microsoft Store instead, you may need to turn off the **python.exe** app execution alias in **Settings** > **Apps** > **Advanced app settings** > **App execution aliases**, and then open a new terminal.

## Get the lab files

1. In Visual Studio Code, open the Command Palette (*Ctrl+Shift+P*, or on the **View** menu, select **Command Palette**), enter the `Git: Clone` command, and clone `https://github.com/GraemeMalcolm/claude-labs` to a local folder of your choice.
1. When the clone is complete, open the folder when prompted.

    The lab files include a starter folder for each application (for example, **/computer-history-client** and **/managed-agent-client**). You'll work in these folders in the labs that follow.

## Summary

You now have a Claude account and an individual Claude Console account, and you've installed Visual Studio Code, Git, and Python. You've also cloned the lab files, so you're ready to start the first Claude API lab.
