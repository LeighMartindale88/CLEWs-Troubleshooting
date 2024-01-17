from flask import Flask, request, jsonify, Response
import os
import re
import fnmatch
from collections import defaultdict
import tempfile
from werkzeug.utils import secure_filename

application = Flask(__name__)

from flask import render_template

@application.route('/')
def home():
    return render_template('index1.html')

@application.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('file')
    if not file:
        return jsonify({"error": "No file provided."})
    file_path = os.path.join(tempfile.gettempdir(), secure_filename(file.filename))
    file.save(file_path)

all_flagged_lines = []


def is_float(value):
    try:
        float(value)
        return True
    except ValueError:
        return False

#Part 1

def read_gams_data_file(file_path):
    with open(file_path, 'r') as file:
        data = []
        line_number = 0
        skip_params = ['ResidualCapacity', 'TechnologyActivityByModeLowerLimit', 'TechnologyActivityByModeUpperLimit','TechnologyActivityIncreaseByModeLimit', 'TechnologyActivityDecreaseByModeLimit', 'InputActivityRatio', 'OutputActivityRatio']
        skip_current_section = False
        current_param_name = None
        starting_year = None
        for line in file:
            line_number += 1
            line_content = line.strip()
            if line_content.startswith('*') or line_content.startswith('#') or not line_content:
                continue
            elif line_content.startswith("set YEAR"):
                starting_year = int(re.search(r'\d+', line_content).group())
            elif line_content.startswith("param"):
                param_name = line_content.split()[1]
                skip_current_section = any(param_name.startswith(p) for p in skip_params)
                current_param_name = param_name
            if skip_current_section:
                continue
            else:
                float_values = [float(value) for value in line_content.split() if is_float(value)]
                data.append((line_number, current_param_name, float_values))
        return data, starting_year

def flag_zero_after_non_zero(data):
    flagged_lines = []
    for line_number, param_name, float_values in data:
        for i in range(1, len(float_values)):
            if float_values[i] == 0 and float_values[i - 1] != 0:
                flagged_lines.append((line_number, param_name, float_values))
                break
    return flagged_lines

def process_zero_after_non_zero(filename):
    data, starting_year = read_gams_data_file(filename)
    flagged_lines = flag_zero_after_non_zero(data)

    results = []

    for line_number, param_name, float_values in flagged_lines:
        with open(filename, "r") as file:
            line_content = [line.strip() for index, line in enumerate(file, 1) if index == line_number][0]
        technology, mode, *_ = line_content.split()

        results.append((line_number, param_name, technology, starting_year + float_values.index(0)))

    return results


#Part 2

def read_gams_data_file2(file_path):
    with open(file_path, 'r') as file:
        data = []
        line_number = 0
        current_param_name = None
        current_section_lines = []
        starting_year = None
        for line in file:
            line_number += 1
            line_content = line.strip()
            if line_content.startswith('*') or line_content.startswith('#') or not line_content:
                continue
            elif line_content.startswith("set YEAR"):
                starting_year = int(re.search(r'\d+', line_content).group())
            elif line_content.startswith("param"):
                current_param_name = line_content.split()[1]
            else:
                if line_content.startswith('['):
                    current_section_lines.append(line_content)
                elif current_section_lines:
                    split_values = current_section_lines[-1].strip("[]").split(',')
                    technology, mode, commodity = split_values[1], split_values[0], split_values[2] if len(split_values) >= 3 else (None, None, None)
                    float_values = [float(value) for value in line_content.split() if is_float(value)]
                    data.append((line_number, current_param_name, technology, mode, commodity, float_values))
                else:
                    float_values = [float(value) for value in line_content.split() if is_float(value)]
                    data.append((line_number, current_param_name, None, None, None, float_values))
        return data, starting_year

def flag_zeros_in_params(data, target_params):
    flagged_lines = []
    for line_number, param_name, technology, mode, commodity, float_values in data:
        if param_name in target_params:
            for i in range(len(float_values)):
                if float_values[i] == 0:
                    flagged_lines.append((line_number, param_name, technology, mode, commodity, float_values))
                    break
    return flagged_lines

def process_zeros_in_params(filename, target_params):
    data, starting_year = read_gams_data_file2(filename)
    flagged_zeros = flag_zeros_in_params(data, target_params)

    input_activity_ratios = []
    output_activity_ratios = []

    for line_number, param_name, technology, mode, commodity, float_values in flagged_zeros:
        if param_name in target_params:
            if param_name == 'InputActivityRatio':
                input_activity_ratios.append((line_number, technology, mode, starting_year + float_values.index(0)))
            elif param_name == 'OutputActivityRatio':
                output_activity_ratios.append((line_number, technology, mode, starting_year + float_values.index(0)))

    return input_activity_ratios, output_activity_ratios


#Part 3

def is_year(value):
    try:
        year = int(value)
        return 2015 <= year <= 2070
    except ValueError:
        return False

def read_gams_data_file_part3(file_path, data_ranges):
    data_file = open(file_path, "r")
    data_sections = {}
    current_section = None
    line_number_mapping = defaultdict(list)
    for line_number, line in enumerate(data_file, start=1):
        line = line.strip()
        if not line or line.startswith('*'):  # Skip empty lines or comments
            continue
        if line.startswith("set") or line.startswith("param"):
            current_section = line.split()[1].strip(";")
            data_sections[current_section] = []
        elif current_section is not None and current_section in data_ranges:
            data = line.strip().split()
            if len(data) >= 6:  # Only append lines that have at least six fields
                data_sections[current_section].append(data)
                line_number_mapping[current_section].append(line_number)
    data_file.close()
    return data_sections, line_number_mapping

data_ranges = {
    'CapitalCost': (0, 7000),
    'FixedCost': (0, 150),
    'VariableCost': (-5, 100),
    'OperationalLife': (0, 51),
    'CapacityToActivityUnit': (0, 32),
    'CapacityFactors': (0, 1),
    'DiscountRate': (0, 1),
    'ResidualCapacity': (0, 30),
    'EmissionActivityRatio': (0, 1),
    'YearSplit': (0, 1),
    'SpecifiedAnnualDemand': (0, 200),
    'SpecifiedDemandProfile': (0, 1),
    'InputActivityRatio': (0.01, 3),
    'OutputActivityRatio': (0.01, 20000),
    'AccumulatedAnnualDemand': (0, 10000),
}

def check_data_ranges(data_sections, data_ranges, line_number_mapping):
    out_of_range = []
    processed_lines = set()
    for param_name, data in data_sections.items():
        if param_name not in data_ranges:
            continue
        index = 0
        for row in data:
            index += 1
            line_number = line_number_mapping[param_name][index - 1]
            if line_number in processed_lines:
                continue
            values = [float(v) for v in row[5:] if is_float(v) and not is_year(v)]  # Convert the values to float only if they are numbers and not years
            for value in values:
                if value < data_ranges[param_name][0]:
                    out_of_range.append((param_name, line_number, "too small", value))
                    processed_lines.add(line_number)
                    break
                elif value > data_ranges[param_name][1]:
                    out_of_range.append((param_name, line_number, "too big", value))
                    processed_lines.add(line_number)
                    break

    return out_of_range

def process_data_ranges(file_path):
    data_sections, line_number_mapping = read_gams_data_file_part3(file_path, data_ranges)
    out_of_range = check_data_ranges(data_sections, data_ranges, line_number_mapping)

    results = []
    for param_name, line_number, size, value in out_of_range:
        results.append((line_number, param_name, size, value))

    return results


#part 4

def read_gams_data_file_part4(file_path, data_ranges):
    data_file = open(file_path, "r")
    data_sections = {}
    current_section = None
    line_number_mapping = defaultdict(list)
    years = None
    for line_number, line in enumerate(data_file, start=1):
        line = line.strip()
        if not line or line.startswith('*'):  # Skip empty lines or comments
            continue
        if line.startswith("set") or line.startswith("param"):
            current_section = line.split()[1].strip(";")
            data_sections[current_section] = []
        elif current_section is not None and current_section in data_ranges:
            data = line.strip().split()
            if len(data) >= 6:  # Only append lines that have at least six fields
                if not years:
                    years = [int(y) for y in data[5:] if is_year(y)]
                data_sections[current_section].append((data[:5], [float(v) for v in data[5:] if is_float(v)]))
                line_number_mapping[current_section].append(line_number)
    data_file.close()
    return data_sections, line_number_mapping, years

def check_abrupt_changes(data_sections, threshold, target_params, years, line_number_mapping):
    flagged_lines = []
    for param_name, data in data_sections.items():
        if param_name not in target_params:
            continue
        index = 0
        for row in data:
            index += 1
            float_values = row[1]  # Corrected here
            for i in range(2, len(float_values)):
                if (float_values[i - 1] == 0 and float_values[i] != 0) or (float_values[i - 1] != 0 and float_values[i] == 0):
                    flagged_lines.append((param_name, line_number_mapping[param_name][index - 1], row[0][1], row[0][0], row[0][2] if len(row[0]) >= 3 else None, years[i - 1]))
                elif float_values[i - 1] != 0 and float_values[i] != 0:
                    ratio = float_values[i] / float_values[i - 1]
                    if ratio < (1 - threshold) or ratio > (1 + threshold):
                        year = years[i - 1]
                        flagged_lines.append((param_name, line_number_mapping[param_name][index - 1], row[0][1], row[0][0], row[0][2] if len(row[0]) >= 3 else None, year))
                        break
    return flagged_lines

def process_abrupt_changes(file_path, threshold=0.05):
    target_params = {
        'CapitalCost',
        'FixedCost',
        'VariableCost',
        'CapacityFactors',
        'DiscountRate',
        'EmissionActivityRatio',
        'YearSplit',
        'SpecifiedAnnualDemand',
        'SpecifiedDemandProfile',
        'InputActivityRatio',
        'OutputActivityRatio',
        'AccumulatedAnnualDemand',
        'TotalTechnologyAnnualActivityLowerLimit',
        'TotalTechnologyAnnualActivityUpperLimit',
    }

    data_sections, line_number_mapping, years = read_gams_data_file_part4(file_path, target_params)
    flagged_lines = check_abrupt_changes(data_sections, threshold, target_params, years, line_number_mapping)

    flagged_lines_list = []
    if flagged_lines:
        for name, line_number, technology, mode, commodity, year in flagged_lines:
            flagged_lines_list.append((line_number, name, mode, year))

    return flagged_lines_list

# Part 5

def read_gams_data_file5(file_path):
    data_sections = defaultdict(list)
    current_section = None
    with open(file_path, 'r') as file:
        for line_number, line in enumerate(file, start=1):
            line_content = line.strip()
            if line_content.startswith('*') or line_content.startswith('#') or not line_content:
                continue
            elif line_content.startswith("param"):
                current_section = line_content.split()[1]
            else:
                data_sections[current_section].append((line_number, line_content.split()))

    return data_sections

def check_data_consistency(data_sections):
    duplicate_entries = defaultdict(list)
    target_parameters = ['AccumulatedAnnualDemand', 'SpecifiedAnnualDemand']

    for param, data in data_sections.items():
        if param not in target_parameters:
            continue

        first_year = int(data[1][1][0])  # Updated to use the second row for first_year
        for row in data:
            line_number, row_data = row
            if len(row_data) == 1:  # Skip the '[RE1,*,*]:' row
                continue

            seen_data = set()
            commodity = row_data[0]
            for col_index, value in enumerate(row_data[1:]):
                if value != '0' and value in seen_data:
                    year = first_year + col_index
                    duplicate_entries[param].append((commodity, line_number, value, year))
                else:
                    seen_data.add(value)

    return duplicate_entries

def process_data_consistency(file_path):
    data_sections = read_gams_data_file5(file_path)
    duplicates = check_data_consistency(data_sections)

    results = []
    for param, duplicate_values in duplicates.items():
        for commodity, line_number, value, year in duplicate_values:
            results.append((line_number, param, commodity, year))

    return results


# Part 6

necessary_commodities = {
    'BIO', 'ELC001', 'ELC002', 'LFOR', 'LBLT', 'LWAT', 'LOTH', 'WTRPRC', 'AGRWAT', 'WTREVT',
    'WTRGWT', 'WTRSUR', 'PUBWAT', 'PWRWAT', 'AGRDSL', 'TRABIO', 'PVR'
}

necessary_technologies = {
    'MINLND', 'LNDFOR', 'LNDBLT', 'LNDWAT', 'LNDOTH', 'MINPRC', 'DEMAGRSURWAT', 'DEMAGRGWTWAT',
    'DEMPUBSURWAT', 'DEMPUBGWTWAT', 'DEMPWRSURWAT', 'DEMPWRGWTWAT',
    'DEMAGRDSL', 'DEMTRABIO'
}

def check_essential_items(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()
        commodities_line = lines[7].strip()
        technologies_line = lines[9].strip()

    commodities = set(commodities_line.split()[1:])
    technologies = set(technologies_line.split()[1:])

    missing_commodities = necessary_commodities - commodities
    missing_technologies = necessary_technologies - technologies

    return missing_commodities, missing_technologies



#part 7

tech_commodity_mapping = {
    "PWR*": {
        "BIO": "BIO",
        "TRN": "ELC001",
        "OHC": ["OIL", "PWRWAT"],
        "SOL": "SOL",
        "PVR": "PVR",
        "HYD": "HYD",
        "COA": ["COA", "PWRWAT"],
        "WND": "WND"
    },
    "LND*HR": ["LND", "WTRPRC", "AGRDSL"],
    "LND*HI": ["LND", "WTRPRC", "AGRWAT", "AGRDSL"],
    "DEMTRABIO": lambda commodity: commodity.startswith("CRP") and len(commodity) == 6,
    "LNDFOR": ["LND", "WTRPRC"],
    "LNDBLT": ["LND", "WTRPRC"],
    "LNDWAT": ["LND", "WTRPRC"],
    "LNDOTH": ["LND", "WTRPRC"],
    "DEMAGRSURWAT": ["ELC002", "WTRSUR"],
    "DEMAGRGWTWAT": ["ELC002", "WTRGWT"],
    "DEMPUBSURWAT": ["ELC002", "WTRSUR"],
    "DEMPUBGWTWAT": ["ELC002", "WTRGWT"],
    "DEMPWRSURWAT": ["ELC002", "WTRSUR"],
    "DEMPWRGWTWAT": ["ELC002", "WTRGWT"],
}

def get_mapping(tech):
    for pattern, mapping in tech_commodity_mapping.items():
        if fnmatch.fnmatch(tech, pattern) or tech == pattern:
            if isinstance(mapping, dict):
                for subpattern, commodity in mapping.items():
                    if tech.startswith("PWR"):
                        if re.search(subpattern, tech[3:]):
                            return commodity
            else:
                return mapping
    return None

def check_technology_commodity_match(filename):
    pattern = re.compile(r"\[RE1,(\w+),(\w+),[^,\]]+,\*")
    flagged_lines = []

    with open(filename, "r") as file:
        in_input_activity_ratio_section = False

        for line_number, line in enumerate(file, 1):
            line = line.strip()
            if line.startswith("param InputActivityRatio"):
                in_input_activity_ratio_section = True
            elif line.startswith("param") or line.startswith(";"):
                in_input_activity_ratio_section = False
            elif in_input_activity_ratio_section:
                match = pattern.match(line)
                if match:
                    technology, commodity = match.groups()

                    expected_commodity = get_mapping(technology)
                    if expected_commodity:
                        if isinstance(expected_commodity, list) and commodity not in expected_commodity:
                            flagged_lines.append((line_number, technology, commodity))
                        elif callable(expected_commodity) and not expected_commodity(commodity):
                            flagged_lines.append((line_number, technology, commodity))
                        elif not isinstance(expected_commodity, list) and not callable(expected_commodity) and commodity != expected_commodity:
                            flagged_lines.append((line_number, technology, commodity))
                    else:
                        flagged_lines.append((line_number, technology, "UNEXPECTED"))

    return flagged_lines



        #Part 8

#Part 8

tech_commodity_mapping_output = {
    "MIN*": {
        "BIO": "BIO",
        "OIL": "OIL",
        "SOL": "SOL",
        "HYD": "HYD",
        "COA": "COA",
        "WND": "WND",
        "LND": "LND",
        "PRC": "WTRPRC",
    },
    "PWR*": {
        "BIO": "ELC001",
        "TRN": "ELC002",
        "OHC": "ELC001",
        "SOL": "ELC001",
        "PVR": "ELC002",
        "HYD": "ELC001",
        "COA": "ELC001",
        "WND": "ELC001",
    },
    "LND*": {
        "FOR": ["LFOR", "WTREVT", "WTRGWT", "WTRSUR"],
        "BLT": ["LBLT", "WTREVT", "WTRGWT", "WTRSUR"],
        "WAT": ["LWAT", "WTREVT", "WTRGWT", "WTRSUR"],
        "OTH": ["LOTH", "WTREVT", "WTRGWT", "WTRSUR"],
    },
    "MINPRC": "WTRPRC",
    "DEMAGRSURWAT": "AGRWAT",
    "DEMAGRGWTWAT": "AGRWAT",
    "DEMPUBSURWAT": "PUBWAT",
    "DEMPUBGWTWAT": "PUBWAT",
    "DEMPWRSURWAT": "PWRWAT",
    "DEMPWRGWTWAT": "PWRWAT",
    "DEMAGRDSL": "AGRDSL",
    "DEMTRABIO": "TRABIO",
}

def check_technology_commodity_match_output(filename):
    pattern = re.compile(r"\[RE1,(\w+),(\w+),[^,\]]+,\*")
    flagged_lines = []

    with open(filename, "r") as file:
        in_output_activity_ratio_section = False

        for line_number, line in enumerate(file, 1):
            line = line.strip()
            if line.startswith("param OutputActivityRatio"):
                in_output_activity_ratio_section = True
            elif line.startswith("param") or line.startswith(";"):
                in_output_activity_ratio_section = False
            elif in_output_activity_ratio_section:
                match = pattern.match(line)
                if match:
                    technology, commodity = match.groups()

                    if not is_valid_mapping(technology, commodity, tech_commodity_mapping_output):
                        flagged_lines.append((line_number, technology, commodity))

    return flagged_lines

def is_valid_mapping(technology, commodity, mappings):
    prefix, rest = technology[:3], technology[3:]

    if technology == "MINSOL" and commodity == "PVR":
        return True

    if prefix == "MIN":
        if rest in mappings["MIN*"]:
            return commodity == mappings["MIN*"][rest]
        else:
            return False
    elif prefix == "IMP":
        if len(rest) == 3:
            return commodity.startswith("CRP") and rest == commodity[3:]
        else:
            return False
    elif prefix == "LND":
        if rest in ["FOR", "BLT", "WAT", "OTH"]:
            return commodity in mappings["LND*"][rest]
        else:
            return commodity in ["WTREVT", "WTRGWT", "WTRSUR"] or (commodity.startswith("CRP") and (technology.endswith("HR") or technology.endswith("HI")))
    elif prefix == "PWR":
        tech_key = rest[:3]
        if tech_key in mappings[prefix + "*"]:
            return commodity == mappings[prefix + "*"][tech_key]
        else:
            return False
    elif technology in mappings:
        return commodity == mappings[technology]
    else:
        return False


#Section 2


# Part 1
@application.route('/zero_after_non_zero', methods=['POST'])
def zero_after_non_zero():
    file = request.files.get('file')
    if file:
        file.save('temp_file.txt')
        results = process_zero_after_non_zero('temp_file.txt')
        os.remove('temp_file.txt')

        formatted_results = [
            f"• line {line_number}. {param_name}, {technology}, year {year}"
            for line_number, param_name, technology, year in results
        ]
        message = "Hey! We found a zero after a non-zero value at:\n" + "\n".join(formatted_results)

        return Response(message, content_type='text/plain'), 200
    else:
        return jsonify({"error": "No file provided."})


# Part 2
@application.route('/zeros_in_params', methods=['POST'])
def zeros_in_params():
    if 'file' in request.files:
        file = request.files['file']
        file_path = os.path.join(tempfile.gettempdir(), secure_filename(file.filename))
        file.save(file_path)

        # Define your target_params here as a list of parameter names, for example:
        target_params = ["InputActivityRatio", "OutputActivityRatio"]

        input_activity_ratios, output_activity_ratios = process_zeros_in_params(file_path, target_params)

        formatted_iar = [
            f"• line {line_number}. {technology}, mode {mode}, year {year}"
            for line_number, technology, mode, year in input_activity_ratios
        ]
        formatted_oar = [
            f"• line {line_number}. {technology}, mode {mode}, year {year}"
            for line_number, technology, mode, year in output_activity_ratios
        ]

        message = "Oi Muppet! We found a zero in the:\n"
        message += "InputActivityRatio:\n" + "\n".join(formatted_iar) + "\n"
        message += "OutputActivityRatio:\n" + "\n".join(formatted_oar)

        return Response(message, content_type='text/plain'), 200
    else:
        return jsonify({"error": "File not provided"}), 400


# Part 3
@application.route('/check-data-ranges', methods=['POST'])
def check_data_ranges_route():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file provided'}), 400

    file_path = os.path.join("temp", file.filename)
    file.save(file_path)

    data_sections, line_number_mapping = read_gams_data_file_part3(file_path, data_ranges)
    out_of_range = check_data_ranges(data_sections, data_ranges, line_number_mapping)

    os.remove(file_path)

    if out_of_range:
        out_of_range_formatted = "\n".join(
            [f"• '{param_name}' is {size} ({value}) at line {line_number}." for param_name, line_number, size, value in out_of_range])
        message = f"Whoa! We found a value that might be out of sensible range in:\n{out_of_range_formatted}"
    else:
        message = "All data values are within the specified ranges."

    return Response(message, content_type='text/plain'), 200

# Part 4

@application.route('/abrupt_changes', methods=['POST'])
def abrupt_changes():
    if 'file' in request.files:
        file = request.files['file']
        file_path = os.path.join(tempfile.gettempdir(), secure_filename(file.filename))
        file.save(file_path)

        flagged_lines = process_abrupt_changes(file_path)

        formatted_lines = [
            f"• line {line_number}. See {name}, {mode}, year {year}"
            for line_number, name, mode, year in flagged_lines
        ]
        message = "Hmmm...We found an abrupt 5%+ change between values at\n" + "\n".join(formatted_lines)

        return Response(message, content_type='text/plain'), 200
    else:
        return jsonify({"error": "File not provided"}), 400




#Part 5

@application.route('/check_data_consistency', methods=['POST'])
def check_data_consistency_route():
    file_path = request.form['file_path']
    data_sections = read_gams_data_file5(file_path)
    duplicates = check_data_consistency(data_sections)

    duplicate_values_list = []
    for param, duplicate_values in duplicates.items():
        param_duplicate_values = f"• {param}:\n"
        for commodity, line_number, value, year in duplicate_values:
            param_duplicate_values += f"  - at line {line_number}. {commodity}, in year {year}, Value: '{value}'\n"
        duplicate_values_list.append(param_duplicate_values)

    duplicate_values_text = "\n".join(duplicate_values_list)
    response = f"Uh-oh! We found duplicate values:\n{duplicate_values_text}"

    return response, 200, {'Content-Type': 'text/plain'}



#part 6

@application.route('/check_essential_items', methods=['POST'])
def check_essential_items_route():
    file_path = request.form['file_path']
    missing_commodities, missing_technologies = check_essential_items(file_path)

    missing_commodities_list = "\n".join([f"• {commodity}" for commodity in missing_commodities])
    missing_technologies_list = "\n".join([f"• {technology}" for technology in missing_technologies])

    commodities_message = (
        f"The following necessary commodities are missing or mispelt:\n{missing_commodities_list}"
        if missing_commodities
        else "All necessary commodities are present."
    )
    technologies_message = (
        f"The following necessary technologies are missing or mispelt:\n{missing_technologies_list}"
        if missing_technologies
        else "All necessary technologies are present."
    )

    response = f"{commodities_message}\n\n{technologies_message}"

    return response, 200, {'Content-Type': 'text/plain'}


#Part 7

@application.route('/check_technology_commodity_match', methods=['POST'])
def check_technology_commodity_match_route():
    file_path = request.form['file_path']
    flagged_lines = check_technology_commodity_match(file_path)

    formatted_lines = [
        f"• 'UNEXPECTED' Commodity inputting to Technology '{technology}' (Line {line_number})"
        if commodity == "UNEXPECTED"
        else f"• '{commodity}' Commodity inputting to Technology '{technology}' (Line {line_number})"
        for line_number, technology, commodity in flagged_lines
    ]

    response = "\n".join(formatted_lines)

    return response, 200, {'Content-Type': 'text/plain'}


#Part 8


@application.route('/check_technology_commodity_match_output', methods=['POST'])
def check_technology_commodity_match_output_route():
    file_path = request.form['file_path']
    flagged_lines = check_technology_commodity_match_output(file_path)

    if flagged_lines:
        message = "We found mismatched OUTPUT technology-commodity pairs:\n"
        flagged_lines_str = "\n".join(
            [f"• line {line_number}. See {technology}, {commodity}" for line_number, technology, commodity in flagged_lines]
        )
        response = f"{message}{flagged_lines_str}"
    else:
        response = "All OUTPUT technology-commodity pairs are correct."

    return response, 200, {'Content-Type': 'text/plain'}


# final
@application.route('/check_all', methods=['POST'])
def check_all():
    file = request.files.get('file')
    if not file:
        return "Error: No file provided.", 400
    file_path = os.path.join(tempfile.gettempdir(), secure_filename(file.filename))
    file.save(file_path)

    # Define your target_params here as a list of parameter names, for example:
    target_params = ["InputActivityRatio", "OutputActivityRatio"]

    # Call all the functions
    # Make sure all these functions return plain text responses
    zero_after_non_zero_result = process_zero_after_non_zero(file_path)
    zeros_in_params_result = process_zeros_in_params(file_path, target_params)
    abrupt_changes_result = process_abrupt_changes(file_path)
    data_sections_part5 = read_gams_data_file5(file_path)
    duplicates_result = check_data_consistency(data_sections_part5)
    data_sections_part3, line_number_mapping = read_gams_data_file_part3(file_path, data_ranges)
    out_of_range_result = check_data_ranges(data_sections_part3, data_ranges, line_number_mapping)
    missing_commodities_set, missing_technologies_set = check_essential_items(file_path)
    missing_commodities_result = list(missing_commodities_set)
    missing_technologies_result = list(missing_technologies_set)
    flagged_lines_input_result = check_technology_commodity_match(file_path)
    flagged_lines_output_result = check_technology_commodity_match_output(file_path)

    # Don't forget to clean up and remove the saved file
    os.remove(file_path)

    # Combine the results
    combined_results = f"Zero After Non-Zero:\n{zero_after_non_zero_result}\n\n" \
                       f"Zeros in Params:\n{zeros_in_params_result}\n\n" \
                       f"Abrupt Changes:\n{abrupt_changes_result}\n\n" \
                       f"Duplicates:\n{duplicates_result}\n\n" \
                       f"Out of Range:\n{out_of_range_result}\n\n" \
                       f"Missing Commodities:\n{missing_commodities_result}\n\n" \
                       f"Missing Technologies:\n{missing_technologies_result}\n\n" \
                       f"Flagged Lines Input:\n{flagged_lines_input_result}\n\n" \
                       f"Flagged Lines Output:\n{flagged_lines_output_result}\n\n"


    # Build the response string
    response = ""
    response = f"Line number refers to line in data file (open file in Notepad, use 'Ctrl G' to search line no. for extra clarity on issue)\n\n"
    # Format Zero After Non-Zero
    formatted_zero_after_non_zero = "\n".join([
        f"- At line {line_number}: See {param_name}, {technology}, year {year}"
        for line_number, param_name, technology, year in zero_after_non_zero_result
    ])
    if formatted_zero_after_non_zero:
        response += f"Hey! We found a zero after a non-zero value at:\n{formatted_zero_after_non_zero}\n\n"

    # Format Zeros in Params
    formatted_zeros_in_params_input = "\n".join([
        f"- At line {line_number}. See {param_name}, {technology}, year {year}"
        for line_number, param_name, technology, year in zeros_in_params_result[0]
    ])
    formatted_zeros_in_params_output = "\n".join([
        f"- At line {line_number}. See {param_name}, {technology}, year {year}"
        for line_number, param_name, technology, year in zeros_in_params_result[1]
    ])
    if formatted_zeros_in_params_input or formatted_zeros_in_params_output:
        response += f"Oi Muppet! We found a zero in the InputActivityRatio:\n{formatted_zeros_in_params_input}\n\n" \
                    f"Oi Muppet! We found a zero in the OutputActivityRatio:\n{formatted_zeros_in_params_output}\n\n"

    # Format Abrupt Changes
    formatted_abrupt_changes = "\n".join([
        f"- At line {line_number}. See {param_name}, {technology}, year {year}"
        for line_number, param_name, technology, year in abrupt_changes_result
    ])
    if formatted_abrupt_changes:
        response += f"Hmmm...We found an abrupt 5%+ change between values at\n{formatted_abrupt_changes}\n\n"

    # Format Duplicates
    formatted_duplicates = "\n".join([
        f"- At line {line_number}. {commodity}, in year {year}, Value: '{value}'"
        for param_name, duplicate_list in duplicates_result.items()
        for commodity, line_number, value, year in duplicate_list
    ])
    if formatted_duplicates:
        response += f"Uh-oh! We found duplicate values:\n{formatted_duplicates}\n\n"

    # Format Out of Range
    formatted_out_of_range = "\n".join([
        f"- '{param_name}' is possibly {error_type} ({value}) at line {line_number}."
        for param_name, line_number, error_type, value in out_of_range_result
    ])
    if formatted_out_of_range:
        response += f"Whoa! We found a value that might be out of sensible range in:\n{formatted_out_of_range}\n\n"

    # Format Missing Commodities and Missing Technologies
    formatted_missing_commodities = "\n".join(missing_commodities_result)
    formatted_missing_technologies = "\n".join(missing_technologies_result)

    if formatted_missing_commodities:
        response += f"Missing Commodities:\n{formatted_missing_commodities}\n\n"
    else:
        response += "All necessary commodities are present.\n\n"

    if formatted_missing_technologies:
        response += f"Missing Technologies:\n{formatted_missing_technologies}\n\n"
    else:
        response += "All necessary technologies are present.\n\n"

    return response, 200, {'Content-Type': 'text/plain'}


if __name__ == "__main__":
    for rule in application.url_map.iter_rules():
        print(f"{rule.endpoint}: {rule.rule}")
    application.run(debug=True)

