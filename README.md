Offline build inputs for the sheng Metal add-on workflow.

mesa-work.tar.gz.part-* is the pinned Mesa source with the recorded patches applied.
metal2vulkan.tar.gz.part-* is the pinned translator source without its test corpus.
Each series is split because GitHub rejects files above 100 MiB; concatenate the parts in name order before unpacking.
