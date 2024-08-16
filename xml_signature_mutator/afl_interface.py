"""Wrapper that uses the AFL++ mutator API to run different XML mutators.
This is just an example, you can use it to write your own wrapper."""

import io
import json
import logging
import os
import pathlib
import pickle
import random
import socket
import sys
import time
from datetime import datetime
from operator import add

import yaml
from lxml import etree
from onelogin.saml2.utils import OneLogin_Saml2_XML
from plugin_base import plugin_util

PLUGIN_STATE = {
    "mutators": None,
    "fallback_mutator": None,
    "metrics": None,
    "parser": None,
}

STATE = {
    "last_mutation": None,
    "prob_dist": None,
    "start_time": None,
    "stage_duration": None,
    "last_backup": None,
    "logger": None,
    "seed": None,
    "cfg_dir": None,
    "log_dir": None,
    "backup_dir": None,
}

DATA = {}


def init(seed: bytearray):
    """Called at startup."""

    dont_restore = os.getenv("DONT_RESTORE")
    if dont_restore is None:
        if restore():
            return

    random.seed(str(seed))
    STATE.update({"seed": str(seed)})

    log_dir = os.getenv("LOG_DIR", str(pathlib.Path(__file__).parent.resolve().joinpath(".log/")))
    pathlib.Path(log_dir).mkdir(exist_ok=True, parents=True)
    STATE.update({"log_dir": pathlib.Path(log_dir)})

    cfg_dir = os.getenv(
        "CFG_DIR", str(pathlib.Path(__file__).parent.resolve().joinpath(".config/"))
    )
    STATE.update({"cfg_dir": pathlib.Path(cfg_dir)})

    backup_dir = os.getenv(
        "BACKUP_DIR", str(pathlib.Path(__file__).parent.resolve().joinpath(".log/"))
    )
    pathlib.Path(backup_dir).mkdir(exist_ok=True, parents=True)

    init_logging()
    load_plugins()
    init_prob_dist()
    init_data()
    backup()


def fuzz(buffer: bytearray, additional_buffer: bytearray, max_size: int) -> bytearray:
    """
    Called for every fuzzing operation.

    buffer: the bytearray (buffer) that is to be mutated in this iteration
    additional_buffer: an additional buffer containing data (might be used to, e.g., merge two bufs)
    max_size: maximal size that the result might have
    """

    logger = STATE.get("logger")

    now = datetime.now()

    # Back up state every 600 seconds / 10 minutes
    backup_secs = (now - STATE.get("last_backup")).total_seconds()
    if 600 < backup_secs:
        backup()
    current_stage_secs = (now - STATE.get("start_time")).total_seconds()

    # Adjust probabilities by using metrics and collected data
    if STATE.get("stage_duration") < current_stage_secs:
        handle_stage_change()

    # Handle mutation

    xml_tree = None
    # Check if input is parsable, if not use fallback mutator
    try:
        xml_tree = etree.parse(io.BytesIO(buffer))
    except Exception as exp:
        logger.debug("Input not parsable. Use fallback mutator. %s.", exp)
        mutated_input = exec_fallback_mutator(buffer, additional_buffer, max_size)
        return mutated_input

    root = xml_tree.getroot()
    if len(root.getchildren()) == 0:
        logger.debug("Input has only root element. Most mutators would fail. Chose insert element.")
        mutator = PLUGIN_STATE["mutators"].get("iel")
        mutator_id = mutator.identifier
    else:
        # Choose mutator for mutation based on probability distribution
        mutator = random.choices(
            population=list(PLUGIN_STATE.get("mutators").values()),
            weights=STATE.get("prob_dist").values(),
            k=1,
        ).pop()
        mutator_id = mutator.identifier

    mutated_input = None
    # Perform mutation
    try:
        STATE.update({"last_mutation": mutator_id})
        DATA[mutator_id]["execs"] += 1
        mutated_input = mutator.mutate(buffer, xml_tree, additional_buffer, max_size)
    except Exception as exp:
        logger.error("Uncaught exception during mutate call of %s: %s", mutator_id, exp)
        return bytearray(1)

    # analyze mutated input
    if analyze_result(buffer, mutated_input, mutator_id, max_size) == buffer:
        logger.error("Mutation of %s was not successful. Perform fallback mutation", mutator_id)
        mutated_input = exec_fallback_mutator(buffer, additional_buffer, max_size)

    return mutated_input


def exec_fallback_mutator(buffer, additional_buffer, max_size):
    logger = STATE.get("logger")
    mutator = PLUGIN_STATE.get("fallback_mutator")
    try:
        STATE.update({"last_mutation": "fallback_mutator"})
        DATA["fallback_mutator"]["execs"] += 1
        mutated_input = mutator.mutate(buffer, None, additional_buffer, max_size)

        mutated_input = analyze_result(buffer, mutated_input, "fallback_mutator", max_size)
    except Exception as exp:
        logger.error("Exception caught during fallback mutate call. %s", exp)

    return mutated_input


def describe(max_description_length: int) -> bytearray:
    """Returns name used by AFL to name input

    Args:
        max_description_length (int): Max length of returned name

    Returns:
        bytearray: Name of last mutation as byte array
    """

    return STATE.get("last_mutation").encode(encoding="utf-8")[:max_description_length]


def introspection() -> bytearray:
    """Called by AFL++ when an input triggered a new path, crash or timeout

    Returns:
        str: _description_
    """
    _last_mut = STATE.get("last_mutation")

    STATE.get("logger").debug("New finding with mutator %s.", _last_mut)

    DATA[_last_mut]["new_finds"] += 1

    # we COULD call STATE.get("mutators")[_last_mut] to give feedback to fuzzer!
    # enables smart mutators
    # changing behavior could be triggered after time
    # e.g., after stage time, we change prob that good subtree is chosen instead of random

    return bytearray(_last_mut, encoding="utf-8")


def deinit():
    # i can safe state here
    # called after fuzzing stops
    logger = STATE.get("logger")
    logger.info(json.dumps(DATA, indent=2))
    logger.info(json.dumps(DATA, indent=2))


# def fuzz_count(buffer):
#    try:
#        xml_tree = etree.parse(io.BytesIO(buffer))
#        root = xml_tree.getroot()
#        if len(root.getchildren()) == 0:
#            return 1
#    except Exception:
#        return 1
#    return 19


def init_logging(keep=False) -> None:
    """Init logging for all (sub)modules. Default is INFO. Can be changed with cfg file"""
    logger = logging.getLogger(__name__)
    cfg_dir = STATE.get("cfg_dir")
    logging_cfg_path = cfg_dir.joinpath("logging.yaml")
    log_dir = STATE.get("log_dir")

    filemode = "w"
    if keep:
        filemode = "a"

    # Load logging configuration file
    try:
        with open(logging_cfg_path, encoding="utf-8") as file:
            try:
                logging_cfg = yaml.safe_load(file)
            except yaml.YAMLError as exc:
                sys.exit(
                    "Error reading logging configuration file at: %s. %s.", logging_cfg_path, exc
                )
    except FileNotFoundError as exc:
        sys.exit("Could not load logging configuration file. \n" + str(exc) + "\nAborting...")

    if os.getenv("LOG_LEVEL"):
        log_level = os.getenv("LOG_LEVEL")
    else:
        log_level = logging_cfg.pop("default", "INFO")

    # Set logging config
    if isinstance(logging.getLevelName(log_level), int):
        logging.basicConfig(
            filename=log_dir.joinpath("xml_sugnature_mutator-" + socket.gethostname() + ".log"),
            level=log_level,
            format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
            filemode=filemode,
        )
        logger = logging.getLogger(__name__)
    else:
        logging.basicConfig(
            filename=log_dir.joinpath("xml_sugnature_mutator-" + socket.gethostname() + ".log"),
            level="INFO",
            format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
            filemode=filemode,
        )
        logger = logging.getLogger(__name__)
        logger.warning('Could not set log level %s for default. Use "INFO" instead.', log_level)

    logger.debug("Setting log levels for modules.")
    for module, setting in logging_cfg.items():
        try:
            logging.getLogger(module).setLevel(setting)
            logger.debug("Set log level %s for %s.", setting, module)
        except ValueError as exp:
            logger.warning(
                "Exception when setting log level for %s: %s. \nUse default instead.", module, exp
            )
        except TypeError as exp:
            logger.warning(
                "Exception when setting log level for %s: %s. \nUse default instead.", module, exp
            )

    STATE.update({"logger": logger})


def load_plugins() -> None:
    """Load plugins and create instances as specified in configuration file.

    Args:
        cfg_dir (pathlib.Path): Path to the cfg dir. Default or as given by cmd arguments.
    """
    # configure parbytearray(self._serialize_ to not replace CDATA and DTDs
    parser = etree.XMLParser(strip_cdata=False, resolve_entities=False, remove_comments=False)
    etree.set_default_parser(parser)
    PLUGIN_STATE.update({"parser": parser})

    logger = STATE.get("logger")
    cfg_dir = STATE.get("cfg_dir")

    # /fuzz/config
    if os.getenv("MUTATOR_CFG_PATH"):
        mutators_cfg_path = pathlib.Path(os.getenv("MUTATOR_CFG_PATH"))
    else:
        mutators_cfg_path = cfg_dir.joinpath("mutators.yaml")

    if os.getenv("METRIC_CFG_PATH"):
        metrics_cfg_path = pathlib.Path(os.getenv("METRIC_CFG_PATH"))
    else:
        metrics_cfg_path = cfg_dir.joinpath("metrics.yaml")

    seed = STATE.get("seed")

    logger.info("Loading plugins.")

    with open(mutators_cfg_path, encoding="utf-8") as file:
        plugin_type = "mutator"
        try:
            mutator_cfg = yaml.safe_load(file)
            logger.info("Loaded mutator config file")

            logger.debug("Load mutator plugins")
            plugin_util.load_plugins("mutators.", mutator_cfg["mutator_plugins"])
            tmp_loaded_plugins = {}
            for item in mutator_cfg["mutator_cfg"]:
                logger.debug(f"Creating mutator {item}")
                tmp_plugin = plugin_util.create_plugin(item)
                logger.debug(f"Init mutator")
                try:
                    tmp_plugin.init(seed)
                except:
                    logger.debug("exception during init")
                logger.debug(f"Add mutator to dict of created plugins")
                tmp_loaded_plugins.update({tmp_plugin.identifier: tmp_plugin})
            PLUGIN_STATE.update({"mutators": tmp_loaded_plugins})

            logger.debug("Load fallback mutator")
            # load fallback mutator separately
            tmp_plugin = plugin_util.create_plugin(
                mutator_cfg["fallback_mutator_cfg"].pop()
                | {"identifier": "fallback_mutator"}
            )
            tmp_plugin.init(seed)
            PLUGIN_STATE.update({"fallback_mutator": tmp_plugin})

            plugin_type = "metric"

            with open(metrics_cfg_path, encoding="utf-8") as file:
                metric_cfg = yaml.safe_load(file)
                logger.info("Loaded metric config file")

            logger.debug("Load metric plugins")
            plugin_util.load_plugins("metrics.", metric_cfg["metric_plugins"])
            tmp_loaded_plugins = {}
            for item in metric_cfg["metric_cfg"]:
                logger.debug(f"Creating metric {item}")
                tmp_plugin = plugin_util.create_plugin(item)
                tmp_loaded_plugins.update({tmp_plugin.identifier: tmp_plugin})
                logger.info("Loaded and created plugin %s", tmp_plugin.identifier)
            PLUGIN_STATE.update({"metrics": tmp_loaded_plugins})

        except yaml.YAMLError as exc:
            logger.critical(f"Could not read {plugin_type} config file. Exiting...")
            sys.exit(f"Could not read {plugin_type} config file. Exiting...")
        except ValueError as exp:
            logger.critical(f"Could not create {plugin_type}. {exp}. Aborting...")
            sys.exit("Aborting due to critical error. Check log for information.")
        except TypeError as exp:
            logger.critical(f"Could not create {plugin_type}. {exp}. Aborting...")
            sys.exit("Aborting due to bad configuration. Check log for information.")
        except ModuleNotFoundError as exp:
            logger.critical("Could not create {plugin_type}. {exp}. Aborting...",)
            sys.exit("Aborting due to bad configuration. Check log for information.")


def init_prob_dist() -> None:
    """Initializes the probability distribution for the mutators.
    Utilizes the mutators weight, if no weights are specified, probabilities are
    equally distributed (all mutator weights are 1 per default).
    """

    _prob_dist = list(
        (mutator.identifier, mutator.weight)
        for mutator in list(PLUGIN_STATE.get("mutators").values())
    )

    _prob_dist_dict = {}

    for identifier, weight in _prob_dist:
        _prob_dist_dict.update({identifier: weight})

    STATE.update({"prob_dist": _prob_dist_dict})


def init_data() -> None:
    """Initialize for data collection."""

    for mutator in list(PLUGIN_STATE.get("mutators").keys()) + ["fallback_mutator"]:
        DATA.update(
            {
                mutator: {
                    "execs": 0,
                    "successful_mut": 0,
                    "percent_successful_mut": 0,
                    "well_formed": 0,
                    "percent_well_formed": 0,
                    "saml_valid": 0,
                    "percent_saml_valid": 0,
                    "new_finds": 0,
                    "percent_new_finds": 0,
                }
            }
        )

    STATE.update({"start_time": datetime.now()})
    STATE.update({"last_backup": datetime.now()})
    STATE.update({"stage_duration": int(os.getenv("STAGE_DURATION", "7200"))})


def analyze_result(buffer, mutated_input, mutator_id, max_size):
    """Analyze the mutated_input for mutation success, size conformity, validity and saml_validity.
    Return mutated input if successful, and buffer if not.

    Args:
        buffer (_type_): _description_
        mutated_input (_type_): _description_
        mutator_id (_type_): _description_
        max_size (_type_): _description_
        count_result (bool, optional): _description_. Defaults to True.

    Returns:
        _type_: _description_
    """
    logger = STATE.get("logger")

    if mutated_input is not None:
        if not mutated_input == buffer:
            if 0 < len(mutated_input):
                if len(mutated_input) < max_size:
                    DATA[mutator_id]["successful_mut"] += 1

                    # Check if well_formed
                    well_formed = False
                    try:
                        xml_tree = etree.parse(io.BytesIO(mutated_input))
                        DATA[mutator_id]["well_formed"] += 1
                        well_formed = True
                    except Exception as exp:
                        logger.debug(
                            "Mutated input from %s was not well_formed XML. %s.", mutator_id, exp
                        )

                    if well_formed:
                        # Check if saml valid
                        try:
                            val_result = OneLogin_Saml2_XML.validate_xml(
                                xml_tree.getroot(), "saml-schema-protocol-2.0.xsd"
                            )
                            if isinstance(val_result, etree._Element):
                                DATA[mutator_id]["saml_valid"] += 1

                        except Exception as exp:
                            logger.debug(
                                "Mutated input from %s was not valid SAML. %s.", mutator_id, exp
                            )
                else:
                    logger.info(
                        "Size of mutated input from mutator %s was bigger than max_size", mutator_id
                    )
                    mutated_input = buffer
            else:
                logger.info("Size of mutated input from mutator %s was less than 1", mutator_id)
                mutated_input = buffer
        else:
            logger.info("Mutated input from mutator %s was equal to Input.", mutator_id)
            mutated_input = buffer
    else:
        logger.info("Mutated input from mutator %s was None.", mutator_id)
        mutated_input = buffer

    DATA[mutator_id]["percent_successful_mut"] = round(
        DATA[mutator_id]["successful_mut"] / DATA[mutator_id]["execs"], 7
    )
    DATA[mutator_id]["percent_well_formed"] = round(
        DATA[mutator_id]["well_formed"] / DATA[mutator_id]["execs"], 7
    )
    DATA[mutator_id]["percent_saml_valid"] = round(
        DATA[mutator_id]["saml_valid"] / DATA[mutator_id]["execs"], 7
    )
    DATA[mutator_id]["percent_new_finds"] = round(
        DATA[mutator_id]["new_finds"] / DATA[mutator_id]["execs"], 7
    )

    return mutated_input


def handle_stage_change() -> None:
    logger = STATE.get("logger")
    logger.debug("stage_duration passed")
    STATE.update({"start_time": datetime.now()})

    current_stage_duration: int = STATE.get("stage_duration")

    prob_dist = STATE.get("prob_dist")

    for metric in PLUGIN_STATE.get("metrics").values():
        logger.info("Applying metric")

        prob_dist = metric.evaluate(STATE, DATA)
        new_stage_duration = metric.stage_duration(current_stage_duration, STATE, DATA)

    STATE.update({"prob_dist": prob_dist})
    STATE.update({"stage_duration": new_stage_duration})


def backup() -> None:
    logger = STATE.get("logger")
    logger.critical(json.dumps(DATA, indent=2))
    logger.critical(STATE)
    logger.info("Try to backup state.")
    backup_dir = os.getenv(
        "BACKUP_DIR", str(pathlib.Path(__file__).parent.resolve().joinpath(".backup/"))
    )
    try:
        with open(backup_dir + "/DATA.bak", "wb") as outp:  # Overwrites any existing file.
            pickle.dump(DATA, outp, pickle.HIGHEST_PROTOCOL)
        with open(backup_dir + "/STATE.bak", "wb") as outp:  # Overwrites any existing file.
            pickle.dump(STATE, outp, pickle.HIGHEST_PROTOCOL)
        STATE.update({"last_backup": datetime.now()})
    except Exception as exp:
        logger.critical(
            "Error while backing up state:  %s. Recover after crash likely not possible.", exp
        )


def restore() -> bool:
    print("Try restoring state...")
    global DATA
    global STATE

    backup_dir = os.getenv(
        "BACKUP_DIR", str(pathlib.Path(__file__).parent.resolve().joinpath(".backup/"))
    )
    try:
        with open(backup_dir + "/DATA.bak", "rb") as inp:  # Overwrites any existing file.
            DATA = pickle.load(inp)
        with open(backup_dir + "/STATE.bak", "rb") as inp:  # Overwrites any existing file.
            STATE = pickle.load(inp)
        if DATA and STATE:
            random.seed(STATE.get("seed"))
            init_logging(keep=True)
            load_plugins()
            etree.set_default_parser(PLUGIN_STATE.get("parser"))
            logger = STATE.get("logger")
            logger.info("DATA and STATE restored. Resume fuzzing...")
            return True
    except FileNotFoundError:
        pass
    print("No state to recover. Proceed with initialization.")
    return False


if __name__ == "__main__":

    script_dir = pathlib.Path(__file__).parent
    test_dir = script_dir.joinpath("tests/")
    os.environ["LOG_DIR"] = str(test_dir.joinpath(".log/"))
    os.environ["CFG_DIR"] = str(test_dir.joinpath(".config/"))
    os.environ["INPUT_DIR"] = str(test_dir.joinpath("input/"))
    os.environ["STAGE_DURATION"] = "2"

    try:
        os.remove(script_dir.joinpath(".backup/DATA.bak"))
    except Exception:
        pass
    try:
        os.remove(script_dir.joinpath(".backup/STATE.bak"))
    except Exception:
        pass

    init(time.time())

    input_dir = test_dir.joinpath("input/")
    # change to adjust file
    for file in input_dir.glob("*.xml"):
        print(file)

        # in_file = open(file, "rb") # opening for [r]eading as [b]inary
        # data = in_file.read() # if you only wanted to read 512 bytes, do .read(512)
        # xml_tree = etree.parse(io.BytesIO(data))
        # mutator = PLUGIN_STATE["mutators"].get("dst")
        # mutated_input = mutator.mutate(None, xml_tree, None, 4000)
        # print(mutated_input.decode("utf-8"))
        # exit()

        for i in range(0, 1000):
            with file.open("r+b") as f:
                input_xml = bytearray(f.read())
                res = fuzz(input_xml, b"", 1048576)

    print(json.dumps(DATA, indent=2))

    for _mutator, _stats in DATA.items():
        if _stats.get("percent_successful_mut"):
            assert (
                _stats["percent_successful_mut"] == 1
            ), f"""Mutator {_mutator} failed. Check if this was an
                implementation error or due to randomness / bad luck."""
