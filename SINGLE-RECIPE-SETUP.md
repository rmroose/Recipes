# Publish one Crouton recipe from iPad

This is add-only. An existing Crouton UUID is never overwritten. The existing homepage URL stays the same. Photos and app-only metadata are not needed.

## One-time GitHub configuration
1. Open https://github.com/rmroose/Recipes/settings/pages . Under **Build and deployment → Source**, select **GitHub Actions**. Do this only after `.github/workflows/publish-recipes.yml` and its scripts are installed.
2. In the repository **Actions** tab, select **Publish single recipes → Run workflow → main → Run workflow**. Wait for a green run and check that the live index still has all 11 original entries before using the Shortcut.
3. In your GitHub account settings, go **Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**. Name it `iPad Recipes`, choose an expiration you will renew, resource owner `rmroose`, **Only select repositories → Recipes**, and repository permission **Contents: Read and write**. Metadata read is automatic. No account, administration, Actions, Workflows or other repository permission is needed by the Shortcut.
4. Enter the token only into your own iPad Shortcut. Never send it in chat, put it in a recipe/repository, or share a Shortcut containing it. It gives write access to this whole repository, not only the inbox. Revoke it in GitHub if exposed.

## Shortcut: Publish Crouton Recipe
In Shortcuts create a new Shortcut. Enable **Show in Share Sheet**, accepting Files. Name it `Publish Crouton Recipe`.

1. **Get Text from Input**: Shortcut Input.
2. **Get Dictionary from Input**: the Text. Set variable `Recipe`.
3. **Get Dictionary Value** for `uuid` in Recipe; **Change Case → lowercase**; set variable `RecipeID`.
4. **Get Contents of URL** (GET): `https://api.github.com/repos/rmroose/Recipes/contents/recipe-registry.json?ref=main`, header `Accept: application/vnd.github.raw+json`. Parse as dictionary if needed, get `recipes`, then get the value for `RecipeID`. If it has a value, show `Already published; existing recipe was not changed` and **Stop This Shortcut**.
5. Build a new **Dictionary** called `PublicRecipe` containing just these nine keys and the corresponding values from Recipe. Use **Get Dictionary Value** for each value and use its magic variable, not quoted text. `ingredients` and `steps` must remain arrays, not strings:
   - uuid
   - name
   - ingredients
   - steps
   - serves
   - duration
   - cookingDuration
   - sourceName
   - webLink
   Optional absent fields may be omitted. Do not include images, sourceImage, tags, folderIDs, nutritionalInfo, or the entire original export.
6. **Get Text from Input**: PublicRecipe (its JSON representation), then **Base64 Encode**, with **Line Breaks: None**.
7. **Get Contents of URL**:
   - URL `https://api.github.com/repos/rmroose/Recipes/contents/incoming/[RecipeID].json`
   - Method PUT
   - Headers `Authorization: Bearer YOUR_TOKEN`, `Accept: application/vnd.github+json`
   - Request body JSON: `message` = `Add Crouton recipe`; `content` = Base64 Encoded; `branch` = `main`.
   - Do **not** supply `sha`. That makes an existing inbox file refuse replacement, including simultaneous duplicate submissions.
8. Inspect the response. A successful create contains `content.sha` and `commit.sha`. Only then show `Recipe queued for publication. Check the homepage after GitHub finishes.` Otherwise show the returned error and stop. Do not blindly retry an uncertain upload; check the repository first.
9. Optionally **Open URLs**: `https://rmroose.github.io/Recipes/`. Deployment takes time; refreshing immediately may show the old index. An accepted upload is not a completed deployment.

In Crouton, open one recipe → Share → **File**, then choose this Shortcut. Do not choose Crouton's Link export.

## Status and recovery
- GitHub **Actions → Publish single recipes** shows build/deployment success or exact error.
- `https://rmroose.github.io/Recipes/publish-status.json` reports processed UUIDs; it updates when a deployment succeeds, so it can lag queued uploads.
- Unknown ingredient units or invalid files remain errors instead of being guessed. They do not block other valid inbox recipes.
- If a generated page or index was manually edited, the publisher stops rather than overwriting the edit. Reconcile the registry before retrying.
- Every run scans the whole immutable inbox. Concurrent uploads remain queued. Git pushes use fast-forward protection, retry from the fresh main branch at most three times, and fail visibly rather than losing an update. A failed run can be rerun from Actions.
- Existing UUIDs are retained unchanged. An error for an existing inbox filename does not authorize overwriting it.
- Never use this public repository for private notes. Even inbox JSON is publicly readable, although it is excluded from the Pages deployment.

The repository scripts are locally tested. The Shortcut itself must be built and tested once on the iPad; it is not yet a signed downloadable Shortcut or a verified end-to-end iPad automation.
