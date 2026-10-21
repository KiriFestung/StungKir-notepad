# Сборка для Windows без Windows

Codeberg умеет проверять только на Linux. Для Windows проще всего GitHub: там бесплатно есть настоящие машины с Windows, и закрытого репозитория для этого хватает.

1. Заведи аккаунт на github.com (если его нет).
2. Справа вверху «+» → **New repository**. Название — например, `StungKir`. Выбери **Private** (закрытый, его никто не увидит). Остальное не трогай → **Create repository**.
3. В папке с распакованным StungKir (где лежит `install.sh`) в терминале:

   ```
   git init
   git add .
   git commit -m "StungKir"
   git branch -M main
   git remote add origin https://github.com/ТВОЙ_НИК/StungKir.git
   git push -u origin main
   ```

   При `git push` GitHub попросит войти: вместо пароля нужен токен — Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token, галочка `repo`.
4. На странице репозитория вкладка **Actions** — там уже идёт «Проверка и сборка». Минут через 10–15:
   - зелёная галочка — всё работает и на Linux, и на Windows;
   - красный крестик — открой его, внизу будет, какая проверка не прошла. Пришли этот текст — починим.
5. Готовый установщик для Windows: открой запуск → внизу **Artifacts** → `StungKir-Windows` (архив с `StungKir-Setup-….exe`).

Дальше при каждом `git push` всё повторяется само. Бесплатных минут у закрытого репозитория хватает примерно на 50 таких сборок в месяц.
