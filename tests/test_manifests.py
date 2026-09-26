from pathlib import Path
import re
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / "apps/astro-ai-api/overlays/academy"


class ManifestTests(unittest.TestCase):
    def test_image_is_immutable_and_no_ingress(self):
        overlay = yaml.safe_load((OVERLAY / "kustomization.yaml").read_text())
        self.assertEqual(overlay["resources"], ["../../base"])
        self.assertEqual(overlay["images"][0]["newName"], "ghcr.io/astro-inter/astro-ai-api")
        self.assertTrue(re.fullmatch(r"sha-[0-9a-f]{40}", overlay["images"][0]["newTag"]))

    def test_one_replica_and_registry_secret(self):
        patch = yaml.safe_load((OVERLAY / "deployment-patch.yaml").read_text())
        self.assertEqual(patch["spec"]["replicas"], 1)
        self.assertEqual(patch["spec"]["strategy"]["rollingUpdate"],
                         {"maxSurge": 0, "maxUnavailable": 1})
        self.assertEqual(patch["spec"]["template"]["spec"]["imagePullSecrets"],
                         [{"name": "ghcr-read"}])

    def test_argocd_watches_central_repository(self):
        project, app = yaml.safe_load_all((ROOT / "argocd/academy.yaml").read_text())
        source = app["spec"]["source"]
        self.assertEqual(source["repoURL"], "https://github.com/Astro-Inter/astro-gitops.git")
        self.assertEqual(project["spec"]["sourceRepos"], [source["repoURL"]])
        self.assertEqual(source["targetRevision"], "main")
        self.assertEqual(source["path"], "apps/astro-ai-api/overlays/academy")
        self.assertEqual(app["spec"]["destination"],
                         {"server": "https://kubernetes.default.svc", "namespace": "astro-ai"})

    def test_no_secret_objects_versioned(self):
        for path in ROOT.rglob("*.yaml"):
            if ".git" in path.parts:
                continue
            for obj in yaml.safe_load_all(path.read_text()):
                if isinstance(obj, dict):
                    self.assertNotEqual(obj.get("kind"), "Secret", str(path))

    def test_java_api_is_isolated_and_manual_until_first_release(self):
        base = ROOT / "apps/astro-api/base"
        deploy = yaml.safe_load((base / "deployment.yaml").read_text())
        self.assertEqual(deploy["spec"]["replicas"], 1)
        pod = deploy["spec"]["template"]["spec"]
        self.assertEqual(pod["imagePullSecrets"], [{"name": "ghcr-read"}])
        self.assertFalse(pod["automountServiceAccountToken"])
        container = pod["containers"][0]
        self.assertEqual(container["ports"][0]["containerPort"], 8080)
        self.assertEqual(container["envFrom"][1]["secretRef"]["name"], "astro-api-secrets")
        self.assertTrue(container["securityContext"]["readOnlyRootFilesystem"])
        app = yaml.safe_load((ROOT / "argocd/astro-api.yaml").read_text())
        self.assertEqual(app["spec"]["source"]["targetRevision"], "main")
        self.assertEqual(app["spec"]["source"]["path"], "apps/astro-api/overlays/academy")
        self.assertEqual(app["spec"]["destination"]["namespace"], "astro-api")
        self.assertNotIn("automated", app["spec"]["syncPolicy"])
        project = next(yaml.safe_load_all((ROOT / "argocd/academy.yaml").read_text()))
        self.assertIn({"server": "https://kubernetes.default.svc", "namespace": "astro-api"},
                      project["spec"]["destinations"])

    def test_java_image_is_pending_or_immutable_and_internal(self):
        overlay = yaml.safe_load(
            (ROOT / "apps/astro-api/overlays/academy/kustomization.yaml").read_text())
        self.assertEqual(overlay["images"][0]["newName"], "ghcr.io/astro-inter/astro-api")
        tag = overlay["images"][0]["newTag"]
        self.assertTrue(tag == "pending-first-release" or re.fullmatch(r"sha-[0-9a-f]{40}", tag))
        svc = yaml.safe_load((ROOT / "apps/astro-api/base/service.yaml").read_text())
        self.assertEqual(svc["spec"]["type"], "ClusterIP")
