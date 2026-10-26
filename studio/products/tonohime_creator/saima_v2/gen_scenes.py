"""Scene stills for the two Saima story ads (FLUX.2-klein on the free HF Space, 768x1344).
Image 1 = Saima (selfie_a.png: face + mint kurti + stethoscope), image 2 = the real TONO HIME bottle."""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\Dropship\studio")
from studio import config, hf  # noqa: E402
from studio.util import StudioError  # noqa: E402

HERE = Path(__file__).parent
OUT = HERE / "scenes"
OUT.mkdir(exist_ok=True)
P = Path(r"E:\Dropship\studio\products\tonohime_creator")
SAIMA = P / "work/scenes/selfie_a.png"
BOTTLE = P / "photos/bottle_clear.png"

LOOK = ("She wears the same outfit as in image 1: a pastel mint embroidered kurti, a soft ivory chiffon dupatta, "
        "small gold earrings and a black stethoscope worn loosely around her neck. ")
KEEP = ("Keep the person's face, skin tone, hair and body exactly the same as in image 1 (same identity). "
        "Photorealistic cinematic photo, shot on a full-frame camera with a 35mm lens, shallow depth of field, "
        "natural skin texture, rich colour grade, vertical 9:16. No text, no captions, no logo, no watermark.")
KEEP_P = ("Keep the product exactly as in image 2: same bottle shape, clear cap, red and white label design. ")

S, B = "saima", "bottle"
SCENES = {
    # ---- video 1: Dhaka story ----
    "v1_hatirjheel": ([S], "The person from image 1, chest-up close shot, looking straight into the camera and speaking "
                      "mid-sentence with a confident friendly expression, standing on the Hatirjheel bridge in Dhaka at "
                      "night, the curved lit-up bridge and colourful city lights reflecting on the lake behind her as soft bokeh. "),
    "v1_oldtown": ([S], "The person from image 1 walking toward the camera through a busy Old Dhaka street full of colourful "
                   "cycle rickshaws and old buildings with hanging signboards (signs blurred), holding a small plain brown "
                   "paper bag, natural smile, warm golden afternoon light. "),
    "v1_ahsan": ([S, B], "The person from image 1 standing in front of the pink Ahsan Manzil palace in Old Dhaka with its "
                 "grand staircase and dome behind her, holding the product from image 2 up beside her face toward the "
                 "camera, warm smile, bright clear daylight. "),
    "v1_product": ([B], "The product from image 2 alone, standing on a glossy black wet surface at night, colourful "
                   "blurred city lights bokeh of Dhaka behind, a soft rim light outlining the bottle, premium commercial "
                   "product photography. "),
    "v1_parcel": ([], "A plain unmarked brown cardboard parcel box wrapped with brown tape sitting on a doormat in front "
                  "of a wooden apartment door in Dhaka, soft daylight from a window, clean and private, no text and no logo "
                  "on the box, realistic photo. "),
    "v1_padma": ([S, B], "The person from image 1 at a riverside viewpoint, the long Padma Bridge stretching across the "
                 "wide river behind her at golden sunset, holding the product from image 2 at chest level, warm smile "
                 "looking at the camera, gentle wind moving her dupatta. "),
    # ---- video 2: around Bangladesh ----
    "v2_coxs": ([S], "The person from image 1, chest-up close shot, looking straight into the camera and speaking "
                "mid-sentence with an excited friendly expression, on Cox's Bazar sea beach, waves and the long sandy "
                "shore behind her, golden hour light, sea breeze lifting her dupatta. "),
    "v2_tea": ([S], "The person from image 1 walking along a narrow path between lush green tea bushes in a Sreemangal tea "
               "garden in Sylhet, rolling green hills and shade trees behind, soft morning mist, relaxed smile. "),
    "v2_sajek": ([S, B], "The person from image 1 standing on a wooden resort balcony at Sajek Valley, a sea of white "
                 "clouds and green hills behind her, holding the product from image 2 toward the camera, soft morning "
                 "sunlight, happy expression. "),
    "v2_product": ([B], "The product from image 2 alone standing on smooth wet sand at Cox's Bazar beach, gentle white "
                   "wave foam around its base, golden sunset light and soft sea bokeh behind, premium commercial product "
                   "photography. "),
    "v2_rangamati": ([S], "The person from image 1 standing on the red Rangamati hanging bridge over the blue Kaptai lake, "
                     "green hills behind, one hand on the rope rail, natural smile at the camera, clear afternoon light. "),
    "v2_call": ([S], "The person from image 1 at Cox's Bazar beach at sunset holding a smartphone to her ear as if making a "
                "phone call, smiling warmly at the camera, orange sky and waves behind her. "),
}


def flux(refs, prompt, out, w=576, h=1024):
    from gradio_client import handle_file
    gal = [{"image": handle_file(str(p)), "caption": None} for p in refs]
    r = hf.call(config.SPACE_EDIT_FAST,
                lambda c: c.predict(prompt, gal, "Distilled (4 steps)", 0, True, w, h, 4, 1.0, False, api_name="/infer"))
    return hf.save_output(r, out)


only = set(sys.argv[1:])
for name, (refs, text) in SCENES.items():
    if only and name not in only:
        continue
    out = OUT / f"{name}.png"
    if out.exists():
        print("exists", name)
        continue
    paths = [SAIMA if r == S else BOTTLE for r in refs]
    prompt = text + (LOOK if S in refs else "") + (KEEP if S in refs else "Photorealistic, vertical 9:16, no text, no logo, no watermark. ") + (KEEP_P if B in refs else "")
    try:
        flux(paths, prompt, out)
        print("made", name, flush=True)
    except StudioError as e:
        print("FAIL", name, str(e)[:300], flush=True)
