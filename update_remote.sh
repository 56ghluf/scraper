cd "$1"

if ! git fetch origin prod > /dev/null 2>&1; then
  printf "===== Fetch failed [%s] =====\n" "$(date '+%Y-%m-%d %H:%M:%S')"
  exit 1
fi

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/prod)

if [ "$LOCAL" != "$REMOTE" ]; then
  printf "===== New version detected [%s] =====\n" "$(date '+%Y-%m-%d %H:%M:%S')"
  git reset --hard origin/prod

  "$2" --build build
  chmod +x $0
fi
