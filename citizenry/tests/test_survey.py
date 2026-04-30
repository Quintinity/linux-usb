"""Tests for the hardware self-survey (Slice 1)."""

from citizenry.survey import (
    Accelerator, Camera, Compute, HardwareDelta, HardwareMap, ServoBus,
    _parse_hailortcli_arch, _parse_libcamera_list, _parse_tegra_v4l2_name,
    _parse_cpuinfo, _parse_meminfo,
    merge_capabilities, project_capabilities,
    CAMERA, CSI_CAMERA, USB_CAMERA, COMPUTE,
    HAILO_INFERENCE, NVIDIA_INFERENCE, CORAL_INFERENCE,
    SERVO_BUS, SERVO_FEETECH, SERVO_DYNAMIXEL,
)


def test_parse_libcamera_real_pi5_output():
    sample = """\
Available cameras
-----------------
0 : imx708_wide_noir [4608x2592 10-bit RGGB] (/base/axi/pcie@1000120000/rp1/i2c@80000/imx708@1a)
    Modes: 'SRGGB10_CSI2P' : 1536x864 [120.13 fps - (768, 432)/3072x1728 crop]
                             2304x1296 [56.03 fps - (0, 0)/4608x2592 crop]
"""
    cams = _parse_libcamera_list(sample)
    assert len(cams) == 1
    assert cams[0].kind == "csi"
    assert cams[0].model == "imx708_wide_noir"
    assert cams[0].path == "csi:0"
    assert cams[0].driver == "libcamera"


def test_parse_libcamera_no_cameras():
    assert _parse_libcamera_list("No cameras available!") == []
    assert _parse_libcamera_list("") == []


def test_parse_tegra_v4l2_name_imx219():
    """Real Jetson Orin Nano name string for the IMX219 CSI camera."""
    assert _parse_tegra_v4l2_name("vi-output, imx219 9-0010") == "imx219"


def test_parse_tegra_v4l2_name_imx477():
    assert _parse_tegra_v4l2_name("vi-output, imx477 10-001a") == "imx477"


def test_parse_tegra_v4l2_name_no_sensor():
    assert _parse_tegra_v4l2_name("vi-output") is None
    assert _parse_tegra_v4l2_name("") is None
    assert _parse_tegra_v4l2_name("vi-output, ") is None


def test_parse_cpuinfo_x86():
    sample = """\
processor	: 0
model name	: Intel(R) Core(TM) i5-1035G4 CPU @ 1.10GHz
processor	: 1
model name	: Intel(R) Core(TM) i5-1035G4 CPU @ 1.10GHz
"""
    model, cores = _parse_cpuinfo(sample)
    assert model.startswith("Intel")
    assert cores == 2


def test_parse_cpuinfo_pi5():
    """Pi 5 cpuinfo uses 'Model' (no 'model name' line)."""
    sample = """\
processor	: 0
processor	: 1
processor	: 2
processor	: 3
Model		: Raspberry Pi 5 Model B Rev 1.0
"""
    model, cores = _parse_cpuinfo(sample)
    assert model == "Raspberry Pi 5 Model B Rev 1.0"
    assert cores == 4


def test_parse_meminfo():
    assert _parse_meminfo("MemTotal:        8244268 kB\n") == 7.9


def test_project_capabilities_compute_only():
    hw = HardwareMap(compute=Compute("x", 1, "x86_64", 8.0))
    assert project_capabilities(hw) == [COMPUTE]


def test_project_capabilities_csi_camera():
    hw = HardwareMap(
        cameras=[Camera(kind="csi", model="imx708", path="csi:0", driver="libcamera")],
        compute=Compute("x", 1, "x86_64", 8.0),
    )
    caps = project_capabilities(hw)
    assert COMPUTE in caps and CAMERA in caps and CSI_CAMERA in caps
    assert USB_CAMERA not in caps


def test_project_capabilities_both_camera_kinds():
    hw = HardwareMap(
        cameras=[
            Camera(kind="csi", model="imx708", path="csi:0", driver="libcamera"),
            Camera(kind="usb", model="C920", path="/dev/video2", driver="v4l2"),
        ],
        compute=Compute("x", 1, "x86_64", 8.0),
    )
    caps = project_capabilities(hw)
    assert CSI_CAMERA in caps and USB_CAMERA in caps


def test_parse_hailortcli_hailo8l():
    sample = """\
Executing on device: 0001:01:00.0
Identifying board
Control Protocol Version: 2
Firmware Version: 4.23.0 (release,app,extended context switch buffer)
Logger Version: 0
Board Name: Hailo-8
Device Architecture: HAILO8L
Serial Number: HLDDLBB244602576
"""
    kind, tops = _parse_hailortcli_arch(sample)
    assert kind == "hailo8l" and tops == 13.0


def test_parse_hailortcli_hailo8():
    sample = "Device Architecture: HAILO8\n"
    kind, tops = _parse_hailortcli_arch(sample)
    assert kind == "hailo8" and tops == 26.0


def test_parse_hailortcli_unknown_falls_through():
    kind, tops = _parse_hailortcli_arch("")
    assert kind == "hailo8" and tops is None


def test_project_capabilities_hailo():
    hw = HardwareMap(
        accelerators=[Accelerator(kind="hailo8l", model="hailo8l", device="/dev/hailo0", tops=13.0)],
        compute=Compute("x", 1, "x86_64", 8.0),
    )
    caps = project_capabilities(hw)
    assert HAILO_INFERENCE in caps
    assert NVIDIA_INFERENCE not in caps and CORAL_INFERENCE not in caps


def test_project_capabilities_dedupes_accelerators():
    hw = HardwareMap(
        accelerators=[
            Accelerator(kind="hailo8l", model="hailo8l", device="/dev/hailo0", tops=13.0),
            Accelerator(kind="hailo8", model="hailo8", device="/dev/hailo1", tops=26.0),
        ],
        compute=Compute("x", 1, "x86_64", 8.0),
    )
    assert project_capabilities(hw).count(HAILO_INFERENCE) == 1


def test_project_capabilities_servo_feetech():
    hw = HardwareMap(
        servo_buses=[ServoBus(vendor="feetech", port="/dev/ttyACM0",
                              usb_vid="1a86", usb_pid="7523", controller_id=None)],
        compute=Compute("x", 1, "x86_64", 8.0),
    )
    caps = project_capabilities(hw)
    assert SERVO_BUS in caps and SERVO_FEETECH in caps
    assert SERVO_DYNAMIXEL not in caps


def test_project_capabilities_servo_mixed():
    hw = HardwareMap(
        servo_buses=[
            ServoBus(vendor="feetech", port="/dev/ttyACM0", usb_vid="1a86", usb_pid="7523", controller_id=None),
            ServoBus(vendor="dynamixel", port="/dev/ttyUSB0", usb_vid="0403", usb_pid="6014", controller_id="ABC"),
        ],
        compute=Compute("x", 1, "x86_64", 8.0),
    )
    caps = project_capabilities(hw)
    assert SERVO_FEETECH in caps and SERVO_DYNAMIXEL in caps


def test_merge_capabilities_unions_and_dedupes():
    hw = HardwareMap(
        cameras=[Camera(kind="csi", model="imx708", path="csi:0", driver="libcamera")],
        accelerators=[Accelerator(kind="hailo8l", model="hailo8l", device="/dev/hailo0", tops=13.0)],
        compute=Compute("x", 1, "aarch64", 8.0),
    )
    merged = merge_capabilities(["6dof_arm", "gripper", "feetech_sts3215"], hw)
    # base caps preserved, in their original order, at the front
    assert merged[:3] == ["6dof_arm", "gripper", "feetech_sts3215"]
    # projected caps appended
    assert COMPUTE in merged and CAMERA in merged and CSI_CAMERA in merged
    assert HAILO_INFERENCE in merged
    # no duplicates
    assert len(merged) == len(set(merged))


def test_merge_capabilities_no_hardware_returns_base():
    base = ["compute", "govern", "teleop_source"]
    assert merge_capabilities(base, None) == base
    # returned list is independent (mutating it shouldn't affect base)
    out = merge_capabilities(base, None)
    out.append("x")
    assert "x" not in base


def test_to_compact_dict_full_pi_loadout():
    hw = HardwareMap(
        cameras=[Camera(kind="csi", model="imx708_wide_noir", path="csi:0", driver="libcamera")],
        accelerators=[Accelerator(kind="hailo8l", model="hailo8l", device="/dev/hailo0", tops=13.0)],
        servo_buses=[ServoBus(vendor="feetech", port="/dev/ttyACM0",
                              usb_vid="1a86", usb_pid="7523", controller_id="ABC123")],
        compute=Compute("Cortex-A76", 4, "aarch64", 8.0),
    )
    d = hw.to_compact_dict()
    assert d["v"] == 1
    assert d["cam"] == [["csi", "imx708_wide_noir", "csi:0"]]
    assert d["acc"] == [["hailo8l", "/dev/hailo0", 13.0]]
    assert d["srv"] == [["feetech", "/dev/ttyACM0"]]
    assert d["cpu"] == ["Cortex-A76", 4, "aarch64", 8.0]


def test_to_compact_dict_omits_empty_categories():
    hw = HardwareMap(compute=Compute("x", 1, "x86_64", 8.0))
    d = hw.to_compact_dict()
    assert "cam" not in d and "acc" not in d and "srv" not in d
    assert d["cpu"] == ["x", 1, "x86_64", 8.0]


def test_to_full_dict_round_trips_dataclass_fields():
    hw = HardwareMap(
        cameras=[Camera(kind="csi", model="imx708", path="csi:0", driver="libcamera")],
        compute=Compute("x", 1, "aarch64", 8.0),
    )
    d = hw.to_full_dict()
    assert d["v"] == 1
    assert d["cameras"][0] == {
        "kind": "csi", "model": "imx708", "path": "csi:0", "driver": "libcamera",
    }
    assert d["compute"] == {"cpu_model": "x", "cpu_cores": 1, "arch": "aarch64", "ram_gb": 8.0}
    assert "surveyed_at" in d


def test_diff_identical_maps_is_empty():
    cam = Camera(kind="csi", model="imx708", path="csi:0", driver="libcamera")
    a = HardwareMap(cameras=[cam], compute=Compute("x", 1, "aarch64", 8.0))
    b = HardwareMap(cameras=[cam], compute=Compute("x", 1, "aarch64", 8.0))
    delta = a.diff(b)
    assert delta.is_empty()
    assert delta.summary() == "no change"


def test_diff_detects_added_servo_bus():
    prior = HardwareMap()
    feetech = ServoBus(vendor="feetech", port="/dev/ttyACM0",
                       usb_vid="1a86", usb_pid="7523", controller_id=None)
    current = HardwareMap(servo_buses=[feetech])
    delta = current.diff(prior)
    assert not delta.is_empty()
    assert delta.servo_buses_added == [feetech]
    assert delta.servo_buses_removed == []


def test_diff_detects_removed_camera():
    cam = Camera(kind="usb", model="C920", path="/dev/video2", driver="v4l2")
    prior = HardwareMap(cameras=[cam])
    current = HardwareMap()
    delta = current.diff(prior)
    assert delta.cameras_removed == [cam]
    assert delta.cameras_added == []


def test_diff_keys_servo_bus_by_port():
    """A servo controller renumerating to a different /dev path is treated as remove+add."""
    a = ServoBus(vendor="feetech", port="/dev/ttyACM0", usb_vid="1a86", usb_pid="7523", controller_id="X")
    b = ServoBus(vendor="feetech", port="/dev/ttyACM1", usb_vid="1a86", usb_pid="7523", controller_id="X")
    prior = HardwareMap(servo_buses=[a])
    current = HardwareMap(servo_buses=[b])
    delta = current.diff(prior)
    assert delta.servo_buses_added == [b]
    assert delta.servo_buses_removed == [a]


def test_diff_keys_accelerator_by_kind_and_device():
    h = Accelerator(kind="hailo8l", model="hailo8l", device="/dev/hailo0", tops=13.0)
    prior = HardwareMap()
    current = HardwareMap(accelerators=[h])
    delta = current.diff(prior)
    assert delta.accelerators_added == [h]


def test_delta_summary_lists_changes_per_category():
    delta = HardwareDelta(
        cameras_added=[Camera(kind="usb", model="C920", path="/dev/video2", driver="v4l2")],
        servo_buses_removed=[ServoBus(vendor="feetech", port="/dev/ttyACM0",
                                      usb_vid="1a86", usb_pid="7523", controller_id=None)],
    )
    summary = delta.summary()
    assert "+1 cam" in summary
    assert "-1 srv" in summary
