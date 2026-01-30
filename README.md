# STL → OBJ Converter

### Because sometimes you just want to turn an `.stl` into an `.obj` without going to sites that give your PC the binary from of cancer.

This is a **local-only** STL → OBJ converter with a **proper GUI**, built in **PyQt5** using **trimesh**.  

No cloud. No accounts. No telemetry. No “Sign in to export”.  
Just files going in, files coming out. Like it should be.

---

## What This Thing Does

- Converts **STL → OBJ**
- Supports **batch conversion** (multiple files, folders, drag-and-drop chaos)
- Optional **mesh cleanup** for messy STLs
- Optional **vertex welding** so your OBJ isn’t 700 million duplicated points
- Basic transform tools (scale, center, axis swap/flip) so your model doesn’t load sideways like it’s fainted

---

## Exe Available in the Releases Section

Click here just to get the exe. Life is good!


## Installation From Source

### 1) Clone the repo
You know the drill. Download it, clone it, summon it via rituals. Whatever.

### 2) Install requirements
Use the included `requirements.txt`:

- `pip install -r requirements.txt`

### 3) Run it
Run the main script:

- `python main.py`

---

## How To Use It (In Painfully Helpful Detail)

### Step 1: Add STL files

You’ve got options:

- Drag and drop STL files straight into the list
- Drag and drop a folder (it will grab the `.stl` files inside that folder)
- Click **Add Files** and select your STLs like a civilized person

You’ll see your files appear in the list under **Input STL files**.

Tips:
- You can select multiple files in the list (Ctrl/Shift like Windows intended)
- **Remove Selected** removes just the highlighted ones
- **Clear** nukes the whole list (thermonuclear option)

---

### Step 2: Output folder

In the **Output** section:

- If you **leave Output folder blank**, each OBJ will be saved next to its STL
- If you choose an Output folder, everything gets dumped into that folder

Use **Browse…** if you hate typing paths like the rest of us.

---

### Step 3: Naming mode (how your outputs get named)

Under **Naming**, pick one of these:

#### 1) Same name as STL (file.obj)
- `motor.stl` becomes `motor.obj`

Simple. Clean. Predictable.

#### 2) Add suffix (file_converted.obj)
- `motor.stl` becomes `motor_converted.obj`

This is good if you want to keep both side-by-side without overwriting.

#### 3) Custom name
This is for when you want the output to be *your* name, not the file’s name.
You type a base name in **Custom name**.

Example:
- Custom name: `exported_motor`
- Single file: `exported_motor.obj`
- Multiple files: `exported_motor_01.obj`, `exported_motor_02.obj`, etc.

Also:
- It will **avoid overwriting existing files**
- If a name already exists, it’ll auto-add a counter
- Because deleting your work by accident is not a “feature”

If you select Custom name but leave the box empty, the app will complain. Correctly.

---

### Step 4: Options (the spicy stuff)

All the “make the file not terrible” options live on the right.

#### Merge (weld) duplicate vertices
What it does:
- STLs often store triangles as “triangle soup” (each triangle has its own set of vertices)
- This merges identical vertices so the OBJ is smaller and more sane

You usually want this ON unless you have a weird edge case.

#### Validate & cleanup mesh
What it does:
- Tries to remove junk geometry like degenerate faces, duplicate faces, and unreferenced vertices
- Best-effort fixes normals if it can
- Uses version-safe fallbacks, because trimesh versions have opinions

Turn this on if:
- Your STL is cursed
- Your OBJ loads with weird shading or broken surfaces
- You downloaded the STL from a site that feels like it’s held together by duct tape and regret

#### Center mesh to origin
What it does:
- Moves the model so its bounding-box center sits at (0, 0, 0)

Turn this on if:
- Your model shows up a mile away in your viewer
- You’re tired of hunting for it like a lost sock in a wardrobe

#### Swap Y/Z axes
What it does:
- Swaps the Y and Z coordinates

Turn this on if:
- Your model loads “lying down” or upright when it shouldn’t be
- You’re moving between tools with different coordinate conventions

#### Axis flips (Flip X / Flip Y / Flip Z)
What it does:
- Mirrors the model on that axis

Turn this on if:
- Your model is inside-out
- Your coordinate system is having a tantrum
- Your viewer thinks left is right and right is an illegal suggestion

#### Scale factor + presets
What it does:
- Multiplies all vertex coordinates by a factor

Common use:
- STL in millimeters, but you want meters: set scale to `0.001` (or pick the preset)

Presets included:
- mm → m
- cm → m
- m → mm
- inch → mm

If you don’t know what units your STL is in:
- Look at **Extents** in the stats panel
- If it says your “small part” is 120 units wide, that might be mm
- If it says 120,000, that might be micrometers or you’re converting a cathedral

---

### Step 5: Selected file stats (aka “what am I looking at?”)

When you select a file, the **Selected file stats** panel shows:

- Vertices
- Faces
- Bounds (min/max)  
- Extents (size in X/Y/Z)

These numbers are shown with sensible formatting (2 decimal places) because we’re not printing raw floats like a lunatic.

This is useful for:
- sanity-checking scale
- seeing if your model is absurdly large or tiny
- confirming your transforms are doing what you think they’re doing

---

### Step 6: Convert

Hit **Convert Selected (or All)**:

- If you selected items in the list, it converts only those
- If nothing is selected, it converts everything in the list

Conversion runs in a background thread, so the GUI won’t lock up and pretend it died.

You’ll see:
- progress bar updates
- detailed logs per file (export name, vertex/face counts, bounds/extents)

If you need to stop:
- Click **Cancel**
- It will stop after the current file finishes (safe cancellation, not “pull the power cable” cancellation)

---

## Troubleshooting

### “Validate cleanup mesh” errors
This tool supports a wide range of trimesh versions, but if you’re running something ancient, update:

- `pip install --upgrade trimesh`

If a specific STL still breaks cleanup:
- try turning cleanup OFF
- convert anyway
- then re-run with cleanup ON after welding (or send me the file and we’ll exorcise it)

### The OBJ looks inside-out / mirrored / wrong orientation
Try:
- Swap Y/Z
- Flip one axis (usually X or Y)
- Center to origin
- If it still looks wrong, your viewer’s coordinate conventions might be the real villain

### The OBJ is enormous
Turn on:
- Merge vertices

That usually takes the file size from “industrial tragedy” down to “reasonable”.

---

## Notes

- STL files don’t contain materials/UVs in any meaningful way, so OBJ output is geometry-focused.
- Everything is local. No internet. No data leaving your machine.
- If you want an `.mtl` output too, we can add it (even a basic one with a single material so viewers behave consistently).

---

## License
MIT  
Go crazy with it!

---

## Screenshot / GIF section
Add your screenshots here so people instantly understand the vibe:
- The dark navy UI
- The file list with drag/drop
- The options panel
- The log output after conversion

Because nobody reads. They just scroll and judge you.
