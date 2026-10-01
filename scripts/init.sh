#!/usr/bin/env bash
# keel init: set up the .keel/ namespace, the skills symlink, deny rules and the CLAUDE.md import in a project.
# Idempotent: existing files are never overwritten. Run from the project root or pass it as the first argument.
set -euo pipefail

PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT="${1:-$(pwd)}"
PROJECT="$(cd "$PROJECT" && pwd)"
TEMPLATES="$PLUGIN_ROOT/templates/keel"

# The hooks block instead of letting calls through when jq or python3 is missing (System-ADR 0019).
for tool in git python3 jq; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "keel init: '$tool' fehlt im PATH. Ohne es blockieren die keel-Hooks; installiere es zuerst (Linux: Paketverwaltung)." >&2
    exit 2
  fi
done

created=()
skipped=()

copy_templates() {
  while IFS= read -r -d '' src; do
    rel="${src#"$TEMPLATES"/}"
    dst="$PROJECT/.keel/$rel"
    if [ -e "$dst" ]; then
      skipped+=(".keel/$rel")
    else
      mkdir -p "$(dirname "$dst")"
      cp "$src" "$dst"
      created+=(".keel/$rel")
    fi
  done < <(find "$TEMPLATES" -type f -print0)
}

link_skills() {
  mkdir -p "$PROJECT/.claude"
  local link="$PROJECT/.claude/skills"
  if [ -L "$link" ]; then
    skipped+=(".claude/skills (symlink exists)")
  elif [ -e "$link" ]; then
    echo "warning: $link exists and is not a symlink; leaving it alone. Move its contents to .keel/skills/ and replace it with a symlink." >&2
    skipped+=(".claude/skills (directory exists)")
  else
    ln -s "../.keel/skills" "$link"
    created+=(".claude/skills -> ../.keel/skills")
  fi
}

merge_settings() {
  local settings="$PROJECT/.claude/settings.json"
  local deny="$PLUGIN_ROOT/templates/settings/permissions.json"
  [ -f "$settings" ] || echo '{}' > "$settings"
  python3 "$PLUGIN_ROOT/scripts/merge_settings.py" "$settings" "$deny"
  created+=(".claude/settings.json (allow and deny rules merged)")
}

add_import() {
  local claude_md="$PROJECT/CLAUDE.md"
  local line="@.keel/CLAUDE.md"
  if [ -f "$claude_md" ] && grep -qxF "$line" "$claude_md"; then
    skipped+=("CLAUDE.md (import present)")
  else
    { [ -f "$claude_md" ] && cat "$claude_md"; printf '\n%s\n' "$line"; } > "$claude_md.tmp"
    mv "$claude_md.tmp" "$claude_md"
    created+=("CLAUDE.md (import line added)")
  fi
}

add_gitignore() {
  local gi="$PROJECT/.gitignore"
  local line=".keel/work/logs/"
  if [ -f "$gi" ] && grep -qxF "$line" "$gi"; then
    skipped+=(".gitignore (logs entry present)")
  else
    printf '%s\n' "$line" >> "$gi"
    created+=(".gitignore (.keel/work/logs/ added)")
  fi
}

copy_templates
link_skills
merge_settings
add_import
add_gitignore

echo "keel init in $PROJECT"
echo
echo "created:"
for f in "${created[@]}"; do echo "  $f"; done
if [ "${#skipped[@]}" -gt 0 ]; then
  echo "kept (already present):"
  for f in "${skipped[@]}"; do echo "  $f"; done
fi
echo
echo "next: fill in .keel/zielbild.md, .keel/qualitaetsmerkmale.md, .keel/befugnisse.md and .keel/backlog.md"
