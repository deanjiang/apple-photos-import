# apple-photos-import
Scripts and instructions to export google photos and import them into the Photos app on your mac.

## Export Google Photos

Use Google Takeout to download all your photos. Choose tgz format. You will have to manually download each chunk after authentication in a web browser. So choose the largest chuck size possible. In my case, 50G is the largest chunk size allowed.

Once downloaded, run the following command:

```bash
cat takeout-XXXXXXX-{001..0##}.tgz | tar xzivf - -C <OutputDir>
```

Credits: https://gist.github.com/chabala/22ed01d7acf9ee0de9e3d867133f83fb 

The command will combine all the chunks together and extract photos into the ./Takeout subdirectory

You can repeat the above steps for multiple google accounts to combine the images.

## Import to the Photos app

```bash
% APPLE_ID=appleid@icloud.com ./apimport.py <DirToProcess>
```

outputs

retry failed imports

pause on low disk

restart photos every 500 imports

notifications

Skip successful imports

watch for ignored files.

## Delete Google Photos

https://github.com/mrishab/google-photos-delete-tool
