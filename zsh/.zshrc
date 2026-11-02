# The following lines have been added by Docker Desktop to enable Docker CLI completions.
fpath=(/Users/hectorgb/.docker/completions $fpath)
autoload -Uz compinit
(( ${+_comps[docker]} )) || compinit
# End of Docker CLI completions

# Set up fzf key bindings and fuzzy completion
source <(fzf --zsh)
# Set up zoxide for directory navigation
eval "$(zoxide init zsh)"