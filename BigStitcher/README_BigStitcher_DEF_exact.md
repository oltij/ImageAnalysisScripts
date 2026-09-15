# Fiji + BigStitcher Singularity Definition — Exact Working `.def`

## Purpose

This README documents the **exact `.def` file you provided**, without changing any commands, updater syntax, Java handling, paths, or runscript behavior.

Because this definition is already known to work for your setup, the safest approach is to preserve it exactly and treat it as the reproducible build recipe for the BigStitcher container.

---

## Exact definition file

Save this as:

```text
fiji_latest_bigstitcher.def
```

```def
Bootstrap: docker
From: ubuntu:22.04

%labels
    Application Fiji
    Plugin BigStitcher
    Purpose Headless BigStitcher processing

%environment
    export FIJI_HOME=/opt/Fiji.app
    export PATH=$FIJI_HOME:$PATH
    export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64

%post

    apt-get update && apt-get install -y \
        wget \
        unzip \
        ca-certificates \
        openjdk-21-jre-headless \
        xvfb \
        && rm -rf /var/lib/apt/lists/*

    cd /opt

    wget -O Fiji.zip \
        https://downloads.imagej.net/fiji/latest/fiji-latest-linux64-jdk.zip

    unzip Fiji.zip
    rm Fiji.zip

    mv Fiji Fiji.app

    # Remove bundled Zulu JDK to reduce size
    rm -rf /opt/Fiji.app/java

    test -x /opt/Fiji.app/fiji-linux-x64

    cd /opt/Fiji.app

    ./fiji-linux-x64 \
        --headless \
        --update update-site BigStitcher \
        --no-splash || true

    ./fiji-linux-x64 \
        --headless \
        --update \
        --no-splash || true

    chmod -R a+rX /opt/Fiji.app


%runscript

exec /opt/Fiji.app/fiji-linux-x64 "$@"
```

---

## Recommended location

A convenient location is:

```text
/home/oltij/Desktop/ImageAnalysisScripts/Bigstitcher/
```

giving:

```text
/home/oltij/Desktop/ImageAnalysisScripts/Bigstitcher/fiji_latest_bigstitcher.def
```

The built container can sit beside it as:

```text
/home/oltij/Desktop/ImageAnalysisScripts/Bigstitcher/fiji_latest_bigstitcher.sif
```

---

## Create the directory

```bash
mkdir -p /home/oltij/Desktop/ImageAnalysisScripts/Bigstitcher
cd /home/oltij/Desktop/ImageAnalysisScripts/Bigstitcher
```

Check:

```bash
pwd
```

Expected:

```text
/home/oltij/Desktop/ImageAnalysisScripts/Bigstitcher
```

---

## Create the `.def`

```bash
nano fiji_latest_bigstitcher.def
```

Paste the exact definition above.

Save in `nano` with:

```text
Ctrl+O
Enter
Ctrl+X
```

Confirm:

```bash
ls -lh fiji_latest_bigstitcher.def
```

Optional visual check:

```bash
cat fiji_latest_bigstitcher.def
```

---

## Load Singularity on Great Lakes

```bash
module load singularity/4.4.1
```

Verify:

```bash
singularity --version
```

---

## Build the SIF

From the directory containing the `.def`:

```bash
cd /home/oltij/Desktop/ImageAnalysisScripts/Bigstitcher
```

Build with:

```bash
singularity build --fakeroot \
    fiji_latest_bigstitcher.sif \
    fiji_latest_bigstitcher.def
```

If your environment allows a normal build without fakeroot:

```bash
singularity build \
    fiji_latest_bigstitcher.sif \
    fiji_latest_bigstitcher.def
```

Expected output files:

```text
fiji_latest_bigstitcher.def
fiji_latest_bigstitcher.sif
```

---

## What each section does

### Base image

```def
Bootstrap: docker
From: ubuntu:22.04
```

Uses Ubuntu 22.04 as the container base.

### Labels

```def
%labels
    Application Fiji
    Plugin BigStitcher
    Purpose Headless BigStitcher processing
```

Stores descriptive metadata in the SIF.

### Environment

```def
%environment
    export FIJI_HOME=/opt/Fiji.app
    export PATH=$FIJI_HOME:$PATH
    export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
```

Inside the container:

```text
FIJI_HOME=/opt/Fiji.app
JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
```

and the Fiji directory is added to `PATH`.

### Ubuntu packages

The `%post` section installs:

```text
wget
unzip
ca-certificates
openjdk-21-jre-headless
xvfb
```

These provide downloading, archive extraction, HTTPS certificates, Java, and virtual-display support.

### Fiji download

The build downloads:

```text
https://downloads.imagej.net/fiji/latest/fiji-latest-linux64-jdk.zip
```

to:

```text
/opt/Fiji.zip
```

then extracts it and renames the Fiji directory to:

```text
/opt/Fiji.app
```

### Bundled Java removal

The definition removes:

```text
/opt/Fiji.app/java
```

with:

```bash
rm -rf /opt/Fiji.app/java
```

The container instead uses the system Java configured by:

```text
JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
```

### Fiji executable check

The build verifies:

```text
/opt/Fiji.app/fiji-linux-x64
```

exists and is executable:

```bash
test -x /opt/Fiji.app/fiji-linux-x64
```

### BigStitcher updater step

The exact working command is preserved:

```bash
./fiji-linux-x64 \
    --headless \
    --update update-site BigStitcher \
    --no-splash || true
```

The trailing:

```text
|| true
```

means the build continues even if this command returns a nonzero exit status.

This README does not alter that behavior.

### Fiji updater step

The exact working command is:

```bash
./fiji-linux-x64 \
    --headless \
    --update \
    --no-splash || true
```

Again, the existing behavior is preserved exactly.

### Permissions

```bash
chmod -R a+rX /opt/Fiji.app
```

makes the Fiji tree readable and traversable/executable by users inside the container.

### Runscript

```def
%runscript

exec /opt/Fiji.app/fiji-linux-x64 "$@"
```

Running the SIF directly therefore launches Fiji and forwards any supplied arguments.

For example:

```bash
singularity run \
    fiji_latest_bigstitcher.sif \
    --headless \
    --help
```

uses:

```text
/opt/Fiji.app/fiji-linux-x64
```

inside the container.

---

## Verify the built container

### Check Fiji files

```bash
singularity exec \
    fiji_latest_bigstitcher.sif \
    ls -lah /opt/Fiji.app
```

### Check the Fiji launcher

```bash
singularity exec \
    fiji_latest_bigstitcher.sif \
    test -x /opt/Fiji.app/fiji-linux-x64
```

Visible confirmation:

```bash
singularity exec \
    fiji_latest_bigstitcher.sif \
    bash -lc 'test -x /opt/Fiji.app/fiji-linux-x64 && echo "Fiji launcher found"'
```

Expected:

```text
Fiji launcher found
```

### Check Java

```bash
singularity exec \
    fiji_latest_bigstitcher.sif \
    java -version
```

Check `JAVA_HOME`:

```bash
singularity exec \
    fiji_latest_bigstitcher.sif \
    bash -lc 'echo "$JAVA_HOME"'
```

Expected:

```text
/usr/lib/jvm/java-21-openjdk-amd64
```

### Check Fiji headless startup

```bash
singularity exec \
    fiji_latest_bigstitcher.sif \
    /opt/Fiji.app/fiji-linux-x64 \
    --headless \
    --help
```

### Check the runscript

```bash
singularity run \
    fiji_latest_bigstitcher.sif \
    --headless \
    --help
```

---

## Simple headless macro test

Create:

```bash
nano test_fiji_headless.ijm
```

with:

```javascript
print("FIJI_HEADLESS_TEST_OK");
eval("script", "System.exit(0);");
```

Run:

```bash
singularity exec \
    fiji_latest_bigstitcher.sif \
    /opt/Fiji.app/fiji-linux-x64 \
    --headless \
    -macro "$PWD/test_fiji_headless.ijm"
```

Expected output includes:

```text
FIJI_HEADLESS_TEST_OK
```

---

## Check for BigStitcher files

```bash
singularity exec \
    fiji_latest_bigstitcher.sif \
    bash -lc '
        find /opt/Fiji.app \
            -type f \
            \( -iname "*BigStitcher*.jar" -o -iname "*Big_Stitcher*.jar" \) \
            -print
    '
```

The exact JAR filename may depend on the Fiji/BigStitcher version that was downloaded at build time.

---

## Inspect container metadata

```bash
singularity inspect fiji_latest_bigstitcher.sif
```

This should include the labels:

```text
Application Fiji
Plugin BigStitcher
Purpose Headless BigStitcher processing
```

---

## Access Great Lakes files from the container

For Turbo storage:

```bash
singularity exec \
    --bind /nfs/turbo/umms-parent:/nfs/turbo/umms-parent \
    fiji_latest_bigstitcher.sif \
    ls /nfs/turbo/umms-parent
```

This verifies that the container can see the data location used by the image-analysis workflow.

---

## Suggested repository layout

```text
ImageAnalysisScripts/
└── Bigstitcher/
    ├── fiji_latest_bigstitcher.def
    └── README_BigStitcher_DEF_exact.md
```

The built `.sif` can remain on Great Lakes rather than being committed to GitHub.

---

## Preserve the known-working version

Because this `.def` is already working, the safest reproducibility approach is:

1. Keep `fiji_latest_bigstitcher.def` unchanged.
2. Commit that exact file to GitHub.
3. Keep a copy of the successfully built `.sif`.
4. If you experiment with a different definition later, give it a different filename rather than replacing this one.

For example:

```text
fiji_latest_bigstitcher.def
```

can remain the known-working definition, while a future test could be:

```text
fiji_bigstitcher_test_v2.def
```

---

## Optional checksums

Record the exact `.def`:

```bash
sha256sum fiji_latest_bigstitcher.def \
    > fiji_latest_bigstitcher.def.sha256
```

Record the built SIF:

```bash
sha256sum fiji_latest_bigstitcher.sif \
    > fiji_latest_bigstitcher.sif.sha256
```

Later, verify with:

```bash
sha256sum -c fiji_latest_bigstitcher.def.sha256
```

and:

```bash
sha256sum -c fiji_latest_bigstitcher.sif.sha256
```

---

## Minimal build sequence

```bash
cd /home/oltij/Desktop/ImageAnalysisScripts/Bigstitcher

module load singularity/4.4.1

singularity build --fakeroot \
    fiji_latest_bigstitcher.sif \
    fiji_latest_bigstitcher.def
```

Then test:

```bash
singularity exec \
    fiji_latest_bigstitcher.sif \
    /opt/Fiji.app/fiji-linux-x64 \
    --headless \
    --help
```

---

## Summary

The exact `.def` builds:

```text
Ubuntu 22.04
    |
    +--> wget
    +--> unzip
    +--> CA certificates
    +--> OpenJDK 21 headless
    +--> Xvfb
    |
    v
download Fiji Linux JDK package
    |
    v
/opt/Fiji.app
    |
    +--> remove bundled Java
    +--> use system OpenJDK 21
    +--> run BigStitcher updater command
    +--> run Fiji updater command
    +--> set read/execute permissions
    |
    v
fiji_latest_bigstitcher.sif
    |
    v
/opt/Fiji.app/fiji-linux-x64
```

This README intentionally documents the working definition **as-is** and does not propose changes to it.
