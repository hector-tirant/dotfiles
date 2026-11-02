# dotfiles

Configuration files are the key to a personalized terminal experience. Keeping a dotfiles folder where you store and version control your config files ensures they’re safe, portable, and easily shared.

By keeping your .bashrc, .zshrc, and other configuration files under version control, you can:

    Track changes and easily revert to previous versions if something breaks.
    Sync your settings across multiple machines, recreating your setup anywhere.
    Share your configurations with others, helping them improve their own terminal experience.

A powerful approach is to not only track your configuration files but also to include plugins and tools as git submodules in your dotfiles repository. This keeps everything organized and makes it easy to update or share your complete setup.

## Managing Zsh configuration

`scripts/dotfiles` uses Bash and standard macOS/Linux commands; Stow is not
required. The repository location is determined from the script, not from the
current working directory.

To make the command available, add the repository's `scripts` directory to your
PATH (adjust the path if you cloned elsewhere):

```zsh
export PATH="$HOME/dotfiles/scripts:$PATH"
```

Put that line in your `.zshrc` to keep it available in new terminals. Alternatively,
run `./scripts/dotfiles` from the repository without changing PATH.

```zsh
dotfiles --add --zsh ~/.zshrc
dotfiles --add --zsh ~/.zprofile
```

Each regular file is moved to `zsh/` under its original filename, and its original
path becomes an absolute symbolic link. Editing through that link changes the
repository file, so Git detects the edits. Moving the repository breaks these
absolute links.

If the repository file already exists, it takes precedence. An existing local
regular file is preserved beside its original path as
`<filename>.dotfiles-backup.<random suffix>` before linking; the backup path is
printed. If the local file is absent, only the link is created.

**If the supplied path is already any symbolic link, including a broken or
already-managed link, `--add` warns and changes nothing.** Directories and
symbolic links inside the repository's managed paths are rejected. Only `--zsh`
is currently supported. Paths with spaces must be quoted.

To undo the operation:

```zsh
dotfiles --del --zsh ~/.zshrc
```

This requires a link to the expected `zsh/<filename>` file. It removes the link
and moves the repository file back to the supplied configuration path, preserving
its current content. Unrelated links and ordinary local files are not changed.
Any earlier backup remains untouched; `--del` restores the managed file, not the
backup.

The command does not commit or push changes:

```sh
git status
git diff
git add zsh/.zshrc
git commit -m "Track zsh configuration"
git push
```

After `--del`, Git sees the managed file as deleted; stage that deletion if you
want to stop tracking it. Check configuration for secrets before adding it.

### Tests

The optional regression tests require Python 3:

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
```
