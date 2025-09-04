---
description: "Creates new Git worktrees for different development contexts"
allowed-tools:
  [
    "Bash(git worktree:*)",
    "Bash(git checkout:*)",
    "Bash(git branch:*)",
    "Bash(ls:*)",
    "Bash(cd:*)",
  ]
---

# Claude Command: Worktree Add

Creates new Git worktrees for different development contexts with appropriate branch naming conventions.

## Usage

```
/worktree-add feature/option-chain-improvements
/worktree-add fix/data-provider-error
/worktree-add hotfix/security-patch
/worktree-add experiment/new-strategy
```

## Process

1. Validate worktree name and type
2. Create new worktree directory
3. Create and checkout new branch
4. Set up proper branch tracking
5. Display worktree location and next steps

## Example

### Main development continues in original directory

`cd /path/to/main-project`

### Create worktree for AI-assisted feature

`git worktree add ../ai-feature feature/ai-integration`

### Switch to the new worktree

`cd ../ai-feature`

## Worktree Types

**Feature Branches:**

- `feature/`: New functionality or enhancements
- `feat/`: Alias for feature

**Bug Fixes:**

- `fix/`: Bug fixes and corrections
- `bugfix/`: Alias for fix

**Hotfixes:**

- `hotfix/`: Critical production fixes

**Experiments:**

- `experiment/`: Proof of concepts and experiments
- `poc/`: Proof of concept alias

**Documentation:**

- `docs/`: Documentation updates

**Refactoring:**

- `refactor/`: Code restructuring

## Naming Conventions

- Use kebab-case for branch names
- Include descriptive context
- Prefix with appropriate type
- Keep names concise but clear

## Examples

```bash
# Feature development
/worktree-add feature/portfolio-rebalancing

# Bug fix
/worktree-add fix/options-pricing-error

# Documentation update
/worktree-add docs/strategy-implementation-guide

# Experimental work
/worktree-add experiment/jump-diffusion-model
```

## Directory Structure

Worktrees are created in parallel directories:

```
project/
├── main/           # Main worktree
├── feature-abc/    # Feature worktree
└── fix-xyz/        # Fix worktree
```

## Commands

After creation, use:

- `git worktree list` - Show all worktrees
- `git worktree remove <name>` - Remove worktree
- `cd ../<worktree-name>` - Switch to worktree

## Notes

- Each worktree has independent working directory
- Shared Git history and configuration
- Allows parallel development on different features
- Automatic branch creation and checkout
- Proper upstream tracking setup
