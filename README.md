# resound - convert a WAV file to an rSoundSample

Python 3 required.

    resound [flags] file.wav [file2.wav ...]

WAV files are converted to mono, optionally resampled, and converted to 8-bit unsigned audio rSoundSample resources

## Flags:

* `-n name`, `--name`: specify the resource name. Defaults to the input file name (without the extension)
* `-c text`, `--comment`: add an rComment resource
* `-f freq`, `--freq`: specify the frequency, if this is a note for example. May be a number (554.37) or a note (Db5)
* `-r rate`, `--rate`: resample to a new rate. Default rate is whatever the WAV file was.
* `-o file`: Specify output file (default is sound.r)
* `--df`: write the resource data to the data fork

On OS X and Win32, data will be written to the resource fork (and the filetype/auxtype will be set) unless the `--df` flag is used.  Elsewhere, `--df` is implied.
