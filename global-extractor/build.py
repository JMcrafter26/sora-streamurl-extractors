import os
import time
import json

# ../extractors/
extractors_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'extractors')
script_dir = os.path.dirname(os.path.realpath(__file__))

def get_functions(allowed_functions=[]):
    # from the extractors directory, get all the files that end with .js
    files = [f for f in os.listdir(extractors_dir) if f.endswith('.js')]
    extractor_functions = {}

    print('Getting functions from files...')

    # from the files, check if they contain a line with "/* SCHEME START */" and a line with "/* SCHEME END */", if not skip the file
    # for each file with the lines, get the content between the lines and save it to a list
    for file in files:
        with open(os.path.join(extractors_dir, file), 'r') as f:
            content = f.read()
            start = content.find('/* SCHEME START */')
            end = content.find('/* SCHEME END */')
            if start != -1 and end != -1:
                # get the content between the lines
                scheme = content[start + len('/* SCHEME START */'):end]
                # get the function name from the file name
                function_name = file.split('.')[0]
                # check if the function name is in the allowed functions list, if the list is empty, it means all functions are allowed
                if allowed_functions:
                    if function_name not in allowed_functions:
                        print('Function ' + function_name + ' is not in the allowed functions list. Skipping...')
                        continue
                # add the function to the list
                extractor_functions[function_name] = scheme
    
    print(len(extractor_functions), 'functions found.')
    return extractor_functions


def build_extractors(functions):
        # create the output file

    print('Building extractors...')
    with open(os.path.join(script_dir, 'output', 'extractors.js'), 'w') as f:
        # write the header
        f.write('/**\n')
        f.write(' * This file is automatically generated.\n')
        f.write(' * Do not edit this file directly.\n')
        f.write(' * \n')
        f.write(' * Build Time: ' + time.strftime('%Y-%m-%d %H:%M:%S') + '\n')
        f.write(' */\n\n')

        # Check for duplicate function names and class names
        duplicate_functions = [function for function in functions if list(functions).count(function) > 1]
        
        # Extract class names from all function schemes
        all_class_names = []
        for scheme in functions.values():
            # Find all class names in the scheme
            class_names = [line.split('class ')[1].split(' ')[0] for line in scheme.split('\n') if 'class ' in line]
            all_class_names.extend(class_names)
            
        # Check for duplicate class names
        duplicate_classes = [cls for cls in all_class_names if all_class_names.count(cls) > 1]
        
        # remove duplicates from the list, so there are no duplicates
        duplicate_functions = list(set(duplicate_functions))
        duplicate_classes = list(set(duplicate_classes))
        if duplicate_functions:
            print('Duplicate function names found: ' + str(duplicate_functions))
            print('Resolving by removing duplicates...')
            for function in duplicate_functions:
                # remove the function from the list
                del functions[function]
        if duplicate_classes:
            print('Duplicate class names found: ' + str(duplicate_classes))
            print('Resolving by removing duplicates...')
            for cls in duplicate_classes:
                # remove the class from the list
                for function, scheme in functions.items():
                    if cls in scheme:
                        del functions[function]
                        break
        
                    
        
        # remove all instances of content between /* REMOVE_START */ and /* REMOVE_END */
        for function_name, scheme in functions.items():
            start = scheme.find('/* REMOVE_START */')
            end = scheme.find('/* REMOVE_END */')
            if start != -1 and end != -1:
                scheme = scheme[:start] + scheme[end + len('/* REMOVE_END */'):]
                functions[function_name] = scheme
        
        # remove double linebreaks
        for function_name, scheme in functions.items():
            functions[function_name] = scheme.replace('\n\n', '\n')

        # write the functions, with a comment above each function with the function name
        for function_name, scheme in functions.items():
            f.write('/* --- ' + function_name + ' --- */\n')
            f.write(scheme + '\n\n')


        # save the functions to a json file
        with open(os.path.join(script_dir, 'output', 'extractors.json'), 'w') as json_file:
            json.dump(functions, json_file, indent=4)
        print('Extractors built successfully.')

def build_global_extractor(functions, allowed_functions=[]):
    print('Building global extractor...')
    # get global_extractor_scheme.js
    global_extractor_file = os.path.join(script_dir, 'global_extractor_scheme.js')
    with open(global_extractor_file, 'r') as f:
        content = f.read()

        # add header
        header = '/* Replace your extractStreamUrl function with the script below */\n\n'
        header += '/**\n'
        header += ' * @name global_extractor.js\n'
        header += ' * @description Global extractor to be used in Sora Modules\n'
        header += ' * @author Cufiy\n'
        header += ' * @license MIT\n'
        header += ' * @date ' + time.strftime('%Y-%m-%d %H:%M:%S') + '\n'
        header += ' * @note This file is automatically generated.\n'
        header += ' */\n'
        content = content.replace('/* {HEADER} */', header)
        
        # get output from the extractors.js file
        with open(os.path.join(script_dir, 'output', 'extractors.js'), 'r') as f:
            extractors_content = f.read()
            # remove the header (the first 5 lines)
            lines = extractors_content.split('\n')
            # remove the first 5 lines
            lines = lines[6:]
            # join the lines
            extractors_content = '\n'.join(lines)


            # replace the /* {EXTRACTOR_FUNCTIONS} */ with the content
            content = content.replace('/* {EXTRACTOR_FUNCTIONS} */', extractors_content)
        




        # replace the {ALL_PROVIDERS} with the provider names separated by a comma
        providers = ', '.join([function for function in functions])
        content = content.replace('/* {ALL_PROVIDERS} */', providers)

        # replace the /* {PROVIDER_CASES} */ like this:
        # case "bigwarp":
        #   return bigwarpExtractor(url);
        # case "speedfiles":
        #   return speedfilesExtractor(url);
        
        provider_cases = ''
        for function in functions:
            provider_cases += '    case "' + function + '":\n'
            provider_cases += '      try {\n'
            provider_cases += '         return await ' + function + 'Extractor(html, url);\n'
            provider_cases += '      } catch (error) {\n'
            provider_cases += '         console.log("Error extracting stream URL from ' + function + ':", error);\n'
            provider_cases += '         return null;\n'
            provider_cases += '      }\n'
        content = content.replace('/* {PROVIDER_CASES} */', provider_cases)

        # get test/test_providers.txt
        # check if the file exists
        if not os.path.exists(os.path.join(script_dir, 'test', 'test_providers.txt')):
            print('test/test_providers.txt not found. Skipping test providers.')
        else:
            with open(os.path.join(script_dir, 'test', 'test_providers.txt'), 'r') as f:
                test_providers = f.read().splitlines();
            
            # replace the /* {TEST_PROVIDERS} */ with the test providers, line by line
            test_providers_content = ''
            for provider in test_providers:
                test_providers_content += provider + '\n'
            content = content.replace('/* {TEST_PROVIDERS} */', test_providers_content)

        # save file to test/global_extractor_test.js
        with open(os.path.join(script_dir, 'test', 'global_extractor_test.js'), 'w') as f:
            f.write(content)

        # remove TEST SCHEME (/* TEST SCHEME START */)
        start = content.find('/* TEST SCHEME START */')
        end = content.find('/* TEST SCHEME END */')
        if start != -1 and end != -1:
            content = content[:start] + content[end + len('/* TEST SCHEME END */'):]

        # if allowed_functions is empty:
        if allowed_functions:
            with open(os.path.join(script_dir, 'output', 'global_extractor.js'), 'w') as f:
                f.write(content)
        else:
            # save the file to output/global_extractor.js
            content = '/* WARNING: This file contains all the extractors, working and not working and is not recommended to be used. */\n' + content
            with open(os.path.join(script_dir, 'output', 'global_extractor_all.js'), 'w') as f:
                f.write(content)




def build(allowed_functions=[]):
    print(allowed_functions)
    print('Global extractor build started...')
    # get the functions
    functions = get_functions(allowed_functions)
    # create the output directory if it doesn't exist
    if not os.path.exists(os.path.join(script_dir, 'output')):
        os.makedirs(os.path.join(script_dir, 'output'))

    try:
        # build the extractors
        build_extractors(functions)
    except Exception as e:
        print('Error building extractors: ' + str(e))
        return
    
    # try:
    #     # build the global extractor
    #     build_global_extractor(functions)
    # except Exception as e:
    #     print('Error building global extractor: ' + str(e))
    #     return

    build_global_extractor(functions, allowed_functions=allowed_functions)


def test():
    print('Testing global extractor...')
    # run test/global_extractor_test.js with node and wait for test/test_results.json (timeout 20s)
    os.system('node ' + os.path.join(script_dir, 'test', 'global_extractor_test.js'))
    # wait for the file to be created
    timeout = 20
    start_time = time.time()
    while not os.path.exists(os.path.join(script_dir, 'test', 'test_results.json')):
        if time.time() - start_time > timeout:
            print('Timeout waiting for test results.')
            return
        time.sleep(1)
    # read the test results

# {
#   "speedfiles": "passed",
#   "vidmoly": "passed",
#   "filemoon": "failed",
#   "doodstream": "failed",
#   "voe": "passed"
# }


    new_table_content = '<!-- EXTRACTORS_TABLE_START -->\n'
    new_table_content += '| Extractor | Test Passed |\n'
    new_table_content += '| -------- | ------- |\n'
    with open(os.path.join(script_dir, 'test', 'test_results.json'), 'r') as f:
        test_results = json.load(f)
        # based on the test results, update the md table in __file__  '/..' + '/README.md', where <!-- EXTRACTORS_TABLE_START -->
        # and <!-- EXTRACTORS_TABLE_END --> are

        for provider, result in test_results.items():
            # use emojis for the results
            if result == 'passed':
                new_table_content += '| ' + provider + ' | ✅ |\n'
            else:
                new_table_content += '| ' + provider + ' | ❌ |\n'
    
    # read the README.md file
    with open(os.path.join(script_dir, '..', 'README.md'), 'r', encoding='utf-8') as f:
        readme_content = f.read()
        # find the start and end of the table
        start = readme_content.find('<!-- EXTRACTORS_TABLE_START -->')
        end = readme_content.find('<!-- EXTRACTORS_TABLE_END -->')
        if start == -1 or end == -1:
            print('Error: Table not found in README.md')
            return
        # replace the table with the new table
        new_table_content = readme_content[:start] + new_table_content + readme_content[end:]
        # write the file
        with open(os.path.join(script_dir, '..', 'README.md'), 'w', encoding='utf-8') as f:
            f.write(new_table_content)
            print('README.md updated successfully.')
    
    return test_results



if __name__ == "__main__":
    # build the extractors
    startTime = time.time()
    build()
    print("Build completed successfully.")

    test_results = test()
    print("Test completed successfully.")

    allowed_functions = []
    # add the passed extractors to the allowed functions
    for provider, result in test_results.items():
        if result == 'passed':
            allowed_functions.append(provider)
    # build the global extractor again with the allowed functions
    print('Building global extractor with allowed functions...')
    build(allowed_functions=allowed_functions)


    endTime = time.time()
    print("Total time taken: " + str(round(endTime - startTime, 2)) + " seconds.")