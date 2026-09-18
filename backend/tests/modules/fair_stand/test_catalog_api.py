from app.modules.fair_stand.infrastructure.seed_catalog import seed_fair_stand_catalog


def test_bootstrap_requires_auth(client):
    response = client.get("/api/v1/fair-stand/catalog/bootstrap")
    assert response.status_code in {401, 422}


def test_bootstrap_returns_canonical_aggregates(client, db_session, auth_headers):
    seed_fair_stand_catalog(db_session)
    db_session.flush()

    response = client.get("/api/v1/fair-stand/catalog/bootstrap", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["revision"]
    assert len(body["categories"]) == 6
    assert len(body["items"]) == 96
    visible = [item for item in body["items"] if item["catalogVisible"] is True]
    hidden = [item for item in body["items"] if item["catalogVisible"] is not True]
    assert len(visible) == 58
    assert len(hidden) == 38
    shelf = next(item for item in body["items"] if item["itemKey"] == "shelf_100")
    assert shelf["catalogCategory"] == "shelf-showcase"
    assert shelf["catalogPreview"] == "shelf"
    chair = next(item for item in body["items"] if item["itemKey"] == "chair_eames")
    assert chair["modelFile"] == "eames_chair.glb"
    plant = next(item for item in body["items"] if item["itemKey"] == "EXTRA_INDOOR_PLANT_1")
    assert plant["modelFile"] == "indoor_plants.glb"
    sofa = next(item for item in body["items"] if item["itemKey"] == "furniture_sofa_single_classic")
    assert sofa["modelFile"] == "bej_koltuk_1_ciftli_2_tekli.glb"
    tv = next(item for item in body["items"] if item["type"] == "tv")
    door = next(item for item in body["items"] if item["itemKey"] == "door_100")
    assert door["composition"]["mode"] == "recipe"
    assert len(door["composition"]["items"]) == 6
    assert "options" not in door["composition"]
    kit = next(item for item in body["items"] if item["itemKey"] == "furniture_sofa_set_classic")
    assert "mode" not in kit["composition"]
    assert len(kit["composition"]["items"]) == 3
    vw = next(item for item in body["items"] if item["itemKey"] == "VIDEO_WALL_2X2")
    assert vw["videoWall"]["panelItemKey"] == "VIDEO_WALL_PANEL"
    showcase = next(item for item in body["items"] if item["itemKey"] == "wall_showcase_100_2")
    assert showcase["bodyItems"]["glassShelfItemKey"] == "glass_shelf"
    assert "FairStandItemModel" not in body
    assert "SQLAlchemy" not in body


def test_hidden_item_is_not_catalog_visible(client, db_session, auth_headers):
    seed_fair_stand_catalog(db_session)
    db_session.flush()
    response = client.get("/api/v1/fair-stand/catalog/bootstrap", headers=auth_headers)
    panel = next(item for item in response.json()["items"] if item["itemKey"] == "panel_48_5")
    assert panel["catalogVisible"] is False
    assert panel.get("catalogPreview") is None


def test_unknown_item_is_404(client, db_session, auth_headers):
    seed_fair_stand_catalog(db_session)
    db_session.flush()
    response = client.get("/api/v1/fair-stand/items/not-a-real-item", headers=auth_headers)
    assert response.status_code == 404


def test_exact_item_lookup(client, db_session, auth_headers):
    seed_fair_stand_catalog(db_session)
    db_session.flush()
    response = client.get("/api/v1/fair-stand/items/shelf_100", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["itemKey"] == "shelf_100"
    assert response.json()["type"] == "shelf"
