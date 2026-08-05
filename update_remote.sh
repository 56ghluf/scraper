cd $1

git fetch origin prod

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/prod)

if [ "$LOCAL" != "$REMOTE" ]; then
  echo "===== New version detected [$(date '+%Y-%m-%d %H:%M:%S')] ====="
  git reset --hard origin/prod

  cmake --build build
  chmod +x $0
fi
