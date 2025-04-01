# Dreamsettler Page Manager

1. Build project with tag dsuploader:latest (`docker build --tag dsuploader:latest .`)
2. Pick a compose file. 
- The local compose file will mount the current directory's code so you don't have to rebuild the image on code changes. It will also expose port 8000 so you can visit localhost:8000.
- The regular compose file does include the code in the image itself and will not mount the current directory. It only binds port 8000 to localhost and is supposed to be behind a reverse proxy.
3. Copy .env.skeleton somewhere (usually data/, this directory doesn't exist yet) and modify accordingly. Additional instructions in file.
4. `docker compose up -d` (or `docker compose up -f docker-compose.local.yml -d`)
5. Profit?

## Using the STML parser separately
stmlparse.py in flask_app can be imported or ran as a standalone script.
- If using in standalone mode, `script stmlfile.stml` will (make an attempt to) turn the STML page into HTML.
- If using in a library, `from stmlparse import stml_to_html` and call stml_to_html(page_root, document).

`document` is the STML page as a string, `page_root` is the root path to navigate to if a Page Genie page wants to navigate to /.
This is still a work in progress.

## Credits
The sftp_server module is modified and redistributed from https://github.com/timetric/py-sftp-server, under the MIT license.
Large portions of flask_app/auth.py are adopted from https://github.com/miguelgrinberg/flask-oauth-example, under the MIT license. 
The STML specification is by Noble Robot and can be found at https://stml-reference.noblerobot.com/

## License
Also MIT.
