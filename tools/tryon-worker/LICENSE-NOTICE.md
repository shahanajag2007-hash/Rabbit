# Licence notice for tools/tryon-worker

This folder (the STYLEAI try-on worker) builds on **CatVTON** by Zheng Chong et al.
(https://github.com/Zheng-Chong/CatVTON, model weights https://huggingface.co/zhengchong/CatVTON),
which is licensed under the **Creative Commons Attribution-NonCommercial-ShareAlike 4.0** licence
(https://creativecommons.org/licenses/by-nc-sa/4.0/).

Accordingly, the files in this folder are made available under **CC BY-NC-SA 4.0** as well:

- **Attribution:** credit CatVTON (Chong et al., "CatVTON: Concatenation Is All You Need for Virtual
  Try-On with Diffusion Models") when you use or share results.
- **NonCommercial:** do not use the worker, CatVTON or its outputs for commercial purposes.
- **ShareAlike:** changes to these files must be shared under the same licence.

CatVTON's source and weights are downloaded at setup time and are not part of this repository.
The base model `stable-diffusion-v1-5/stable-diffusion-inpainting` (Stable Diffusion 1.5 inpainting) is
under the CreativeML OpenRAIL-M licence, and `stabilityai/sd-vae-ft-mse` under the MIT licence.
MediaPipe models are Apache-2.0.

The rest of the STYLEAI repository is not affected by this notice; the main application talks to the
worker only over HTTP.
