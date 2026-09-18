# Reconstruct the full pack ZIP

Binary ZIP upload is awkward through our GitHub connector, so the pack is stored as **64 base64 parts**.

## Windows (PowerShell)

```powershell
cd dist
.\decode.ps1
# → 2011-room-reverb.zip
Expand-Archive .\2011-room-reverb.zip -DestinationPath .
```

## macOS / Linux

```bash
cd dist
bash decode.sh
unzip 2011-room-reverb.zip
```

Then open `software/Launch Tweak App.bat` (Windows) or `software/launch_tweak_app.sh`.
