# GoShipit Lifecycle

GoShipit uses three broad issue folders:

```text
todo -> execution -> archive
```

`todo` means an issue is available to start.

`execution` means one active run owns the issue and has a dedicated worktree.

`archive` means the issue is closed and no longer part of active work.

Detailed progress is stored as issue metadata:

```text
setup -> investigate -> propose -> implement -> test -> cleanup
```

Cleanup only changes state in two ways:

```text
execution -> todo
execution -> archive
```
