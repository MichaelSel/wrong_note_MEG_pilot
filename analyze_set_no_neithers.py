import json
import csv
import scipy.stats
import numpy as np
import reformat_data
import statistics as stat



#define directories
processed_dir = './processed'
analyzed_dir = './analyzed'
all_data_path = processed_dir + "/MEGp_all_subjects.json"
responses_excluded=0

did_note_take_seriously = ["MEGp0070","MEGp0064","MEGp0059","MEGp0056","MEGp0057","MEGp0034","MEGp0032","MEGp0014"]
did_not_understand = ["MEGp0034"]

all_sets = []
max_blocks = 0

def get_json(path):
        json_file = open(path)
        json_file = json_file.read()
        return json.loads(json_file)

def mean(ls):
        if len(ls)>0:
                return stat.mean(ls)
        return float('NaN')

def make_csv(subs, keys_to_store,filename='/MEGp_results_no_neithers.csv',include_block_level=False):
        subs = [sub for sub in subs if 'analyzed' in sub] #only analyze subjects that have data
        with open(analyzed_dir + filename, 'w', newline='') as file:
                writer = csv.writer(file)
                keys = ['Subject_ID','excluded','pressed_button1','pressed_button2']
                for i in range(len(all_sets)):
                        set_name = 'set_' + str(i+1)
                        keys.append(set_name)
                        for key in keys_to_store:
                                keys.append(set_name + "_" + key)
                                if(include_block_level):
                                        for block_num in range(max_blocks):
                                                keys.append("block_" + str(block_num) + "_" + set_name + "_" + key)
                writer.writerow(keys)

                for s in subs:
                        values = [s['id'],s['excluded'],s['analyzed']['pressed_button1'],s['analyzed']['pressed_button2']]
                        for i in range(len(all_sets)):
                                set_key = all_sets[i]
                                values.append(set_key)
                                if(set_key not in s['analyzed']['sets']):
                                        for key in keys_to_store:
                                                values.append(" ")
                                else:
                                        for key in keys_to_store:
                                                if(key not in s['analyzed']['sets'][set_key]): values.append("ERROR")
                                                values.append(s['analyzed']['sets'][set_key][key])
                                                if(include_block_level):
                                                        for block_num in range(max_blocks):
                                                                values.append(s['analyzed']['sets'][set_key]['blocks'][block_num][key])
                        writer.writerow(values)
        print("Aggregate analysis file saved.")
        return False

def make_json(subs):
        json_export = json.dumps(subs)
        f = open(analyzed_dir + "/MEGp_results_new.json", "w")
        f.write(json_export)
        f.close()
        print("saved data.")

reformat_data.run()

all_subjects = get_json(all_data_path)

excluded = 0

median = stat.median

for s in all_subjects: #every subject in the cohort
        if(s['id'].startswith("MEGp01")): continue #sets starting with MEGp01 belong to the 2nd cohort where the neither buttons were re-introduced

        s['excluded']=False
        s['analyzed']={
                'block':[],
                'sets':{}
        }
        if(s['id'] in did_not_understand):
                print("Excluding "+ s['id'] + " for not understanding instructions")
                excluded+=1
                s['excluded'] = True
        elif (s['id'] in did_note_take_seriously):
                print("Excluding " + s['id'] + " for not engaging with the task")
                excluded += 1
                s['excluded'] = True

        block_ids_to_run = [block['block'] for block in s['blocks']]

        #you can run specific blocks by uncommenting below
        # block_ids_to_run = [1]

        #This task doesn't have a practice block
        # #don't run the practice block:
        # block_ids_to_run.remove(0) #practice block is index 0

        if(len(s['blocks'])>max_blocks):max_blocks=len(s['blocks'])
        for i,block in enumerate(s['blocks']): #every block for the subject
                if(block['block'] not in block_ids_to_run): continue #if it's not in the blocks we want, skip it
                data = {
                        'sets':{},
                        'pressed_button1':0,
                        'pressed_button2': 0,
                }
                for Q in block['choice']: #Q is every question/trial in the block
                        Q['excluded'] = False
                        # Trial level Time-based exclusion should be written here

                        if(Q['name']!='choice'): continue #if not a choice question, continue to next Q

                        if(Q['response']=='1st'):
                                response_pos = 0
                                data['pressed_button1']+=1
                        elif (Q['response'] == '2nd'):
                                response_pos = 1
                                data['pressed_button2'] += 1
                        else:
                                print("there was an error.")
                        necklace = ', '.join([str(digit) for digit in Q['set']])
                        if(necklace not in all_sets):all_sets.append(necklace) #Track all analyzed sets for all subjects in global variable
                        if(necklace not in data['sets']):
                                data['sets'][necklace] = {
                                        'trials_total': 0,
                                        'chose_shifted': 0,
                                        'chose_swapped': 0,
                                        'rts':[],
                                        'rt_shifted':[],
                                        'rt_swapped': [],
                                }
                        # increment trial tally
                        cur_set = data['sets'][necklace]
                        cur_set['trials_total'] +=1
                        cur_set['rts'].append(Q['rt'])
                        if(Q['order'][response_pos]=='shifted'):
                                cur_set['chose_shifted'] += 1
                                cur_set['rt_shifted'].append(Q['rt'])
                        elif (Q['order'][response_pos] == 'swapped'):
                                cur_set['chose_swapped'] += 1
                                cur_set['rt_swapped'].append(Q['rt'])

                s['analyzed']['block'].append(data)

                #once all the per block data was collected(above), append it to subject totales:
                #if the key doesn't exist in the subject level, create it, otherwise, add to it
                for key in data:
                        if (key =="sets"): continue  # don't do it for sets. Sets are handled below
                        try:
                                s['analyzed'][key] += data[key]
                        except:
                                s['analyzed'][key] = data[key]

                if((max(s['analyzed']['pressed_button1'],s['analyzed']['pressed_button2'])>min(s['analyzed']['pressed_button1'],s['analyzed']['pressed_button2'])*4) and s['excluded']!=True):
                        print("Excluding " + s['id'] + " for button bias")
                        excluded += 1
                        s['excluded']=True
                '''Here we handle sets'''
                for st in data['sets']:
                        if(st not in s['analyzed']['sets']):
                                s['analyzed']['sets'][st]={
                                        'blocks': {}
                                }
                        if(i not in s['analyzed']['sets'][st]['blocks']):
                                s['analyzed']['sets'][st]['blocks'][i] = {}
                        for key in data['sets'][st]:
                                try:
                                        s['analyzed']['sets'][st][key] += data['sets'][st][key]
                                except:
                                        s['analyzed']['sets'][st][key] = data['sets'][st][key]
                        for key in data['sets'][st]:
                                s['analyzed']['sets'][st]['blocks'][i][key] = data['sets'][st][key]


        for set in s['analyzed']['sets']:
                necklace = s['analyzed']['sets'][set]
                if(necklace['trials_total']!=0):
                        necklace['%_shifted'] = necklace['chose_shifted'] / necklace['trials_total']
                        necklace['%_swapped'] = necklace['chose_swapped'] / necklace['trials_total']
                        necklace['rt_shifted'] = mean(necklace['rt_shifted'])
                        necklace['rt_swapped'] = mean(necklace['rt_swapped'])
                        necklace['rt'] = mean(necklace['rts'])
                        necklace['rt_shifted:average'] = necklace['rt_shifted'] / necklace['rt']
                        necklace['rt_swapped:average'] = necklace['rt_swapped'] / necklace['rt']
                for key in s['analyzed']['sets'][set]['blocks']:
                        b_necklace = s['analyzed']['sets'][set]['blocks'][key]
                        if (b_necklace['trials_total'] != 0):
                                b_necklace['%_shifted'] = b_necklace['chose_shifted'] / b_necklace['trials_total']
                                b_necklace['%_swapped'] = b_necklace['chose_swapped'] / b_necklace['trials_total']
                                b_necklace['rt_shifted'] = mean(b_necklace['rt_shifted'])
                                b_necklace['rt_swapped'] = mean(b_necklace['rt_swapped'])
                                b_necklace['rt'] = mean(b_necklace['rts'])
                                b_necklace['rt_shifted:average'] = b_necklace['rt_shifted'] / b_necklace['rt']
                                b_necklace['rt_swapped:average'] = b_necklace['rt_swapped'] / b_necklace['rt']

print(str(excluded) + " subjects have been excluded in total")



keys_to_store = ['trials_total','chose_shifted', 'chose_swapped','%_shifted','%_swapped','rt_shifted','rt_swapped','rt','rt_shifted:average','rt_swapped:average']





make_csv(all_subjects, keys_to_store)

make_json(all_subjects)



