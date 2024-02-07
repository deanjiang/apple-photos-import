## Import photos and EXIF 

I found this command line tool to run on MacOS. 


https://rhettbull.github.io/osxphotos/overview.html 

Also read this from the author 
https://forums.macrumors.com/threads/importing-google-takeout-archive-into-photos-app.2414503/ 

```bash
osxphotos import -walk --album "{filepath.parent.name}"  --skip-dups --dup-albums
--sidecar --keyword "{person}" --report takeout_import.csv <DirToProcess>
```


Do not use sidecars or exif options, as they tend to corrupt image files.

Do not import more than 5k photos at once, or the Photos app will stop responding and importing will fail.

## Patching EXIF manually

In rare cases, you will have to fix image meta data manually.  Here is how.

Install exiftool from https://exiftool.org/ 

This following command line is used to patch EXIF data from json files.

```bash
exiftool -r  -tagsfromfile "%d/%F.json" "-GPSAltitude<geodataaltitude" "-gpslatitude<geodatalatitude" "-gpslatituderef<geodatalatitude" "-gpslongitude<geodatalongitude" "-gpslongituderef<geodatalongitude" "-keywords<tags" "-subject<tags" "-caption-abstract<description" "-imagedescription<description" -d "%s" "-datetimeoriginal<phototakentimetimestamp" -ext "*" --ext "json" -overwrite_original -progress <DirToProcess>

```

https://legault.me/post/correctly-migrate-away-from-google-photos-to-icloud 

This will copy all GPS location data, tags, captions, descriptions, dates and time taken information to ALL image and video files. This may leave some *-edited.jpg files untouched though.

