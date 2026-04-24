@echo off
set /p msg="Enter your commit message: "

echo Starting SpecForge AI Unified Deployment...

:: 1. COMMIT CHANGES
echo Committing changes...
git add .
git commit -m "%msg%"

:: 2. PUSH TO RENDER (GITHUB)
echo Pushing to Render (GitHub)...
git push origin production_worker --force

:: 3. PUSH TO HUGGING FACE (WORKER)
echo Preparing Clean Worker Build for Hugging Face...
git checkout --orphan hf-auto-deploy
git rm -rf --cached .

:: Add everything EXCEPT the 'static' folder
git add .
git reset srs_engine/static/
git reset srs_engine_sequence.png 2>NUL

git commit -m "deploy: %msg% (worker-only)"
git push hf hf-auto-deploy:main --force

:: 4. CLEANUP
echo Cleaning up...
git checkout -f production_worker
git branch -D hf-auto-deploy

echo Done! SpecForge AI is now LIVE on Render and Hugging Face!
pause
