# -*- coding: utf-8 -*-

from sepa import sepa19
from datetime import datetime
import csv
import re
from copy import deepcopy
import click
from dateutil.relativedelta import relativedelta
import json

#params
data = dict(
    #filepath = "/home/afita/Documents/agusti/Gospelians/gospelians/rebuts/202301/202301.csv",
    filepath = "/home/afita/Documents/agusti/Gospelians/gospelians/rebuts/202304/202306.csv",
    due_date = '2023-06-21',
    payment_name = '202306 QUOTA GOSPELIANS 3er TRIMESTRE',
    concept = "QUOTA GOSPELIANS 3er TRIM",
    # Constant
    company_name = 'ASSOCIACIO MUSICAL GOSPELIANS DE GIRONA',
    vat = 'G17977521',
    sepa_id = 'ES84000G17977521',
    schmeid = 'ES84019G17977521',
    iban = 'ES3700810146560001150423',
    bic = 'BSABESBBXXX',
    mandate_default_date = '2009-10-31',

)

CSV_HEAD_LINES = 1
CHAR_OFFSET = 55
MANDATE_DEFAULT_DATE = data['mandate_default_date']


# FORMAT MAR
ROW_POS_MANDATE = 2
ROW_POS_NAME = 3
ROW_POS_IBAN = 4
ROW_POS_AMOUNT = 5
ROW_AMOUNT_FACTOR = 100.0

# FORMAT AGUSTI
ROW_POS_MANDATE = 1
ROW_POS_NAME = 2
ROW_POS_IBAN = 3
ROW_POS_AMOUNT = 4
ROW_AMOUNT_FACTOR = 1.0



def get_lines(filepath):
    with open(filepath, 'r') as linescsv:
        res = []
        csvreader = csv.reader(linescsv, delimiter=';')
        for i in range(0, CSV_HEAD_LINES):
            next(csvreader)
        for row in csvreader:
            res.append(row)
        return res

def calculate_iban(acc_number, country_code):
    if not re.match('[a-zA-Z]{2}', country_code):
        raise Exception('Wrong IBAN country code %s'.format(str(country_code)))

    raw_iban = '{}{}00'.format(acc_number, country_code)
    raw_num_iban = ''
    for char in raw_iban:
        if char.isalpha():
            raw_num_iban += str(ord(char) - CHAR_OFFSET)
        else:
            raw_num_iban += char
    iban_check_code = 98 - (int(raw_num_iban) % 97)
    iban_check_code_str = str(iban_check_code).zfill(2)
    iban = '{}{}{}'.format(country_code, iban_check_code_str, acc_number)
    return iban

def get_mandate(mandate_ref, creditor_id, mandate_sign_date=MANDATE_DEFAULT_DATE):

    mandate_info = sepa19.MandateInformation()
    mandate_fields = {
        'mandate_identifier': mandate_ref,
        'date_of_sign': mandate_sign_date,
        'modification_indicator': 'false',
    }

    mandate_info.feed(mandate_fields)
    operation = sepa19.DirectDebitOperation()
    operation_fields = {
        'mandate_information': mandate_info,
        'creditor_identifier': creditor_id,
    }
    operation.feed(operation_fields)
    return operation

# _debtor_info
def get_debtor_info(line):
    debtor_info = {}
    nom = line[ROW_POS_NAME]
    iban = calculate_iban(line[ROW_POS_IBAN], 'ES')

    debtor = sepa19.GenericPhysicalLegalEntity('Dbtr')

    debtor_fields = {
        'entity_name': nom
    }
    account_id = sepa19.AccountIdentification()
    account_id_fields = {
        'iban': iban
    }
    account = sepa19.BankAccount('DbtrAcct')
    account_id.feed(account_id_fields)
    account_fields = {
        'account_identification': account_id
    }
    agent_id = sepa19.AgentIdentifier()
    agent_id_fields = {
    #    'bic': to_ascii(bic)
    }
    agent = sepa19.BankAgent('DbtrAgt')
    agent_id.feed(agent_id_fields)
    agent_fields = {
            'agent_identifier': agent_id
    }

    debtor.feed(debtor_fields)
    agent.drop_empty = False
    agent.feed(agent_fields)
    account.feed(account_fields)

    debtor_info['debtor'] = debtor
    debtor_info['agent'] = agent
    debtor_info['account'] = account
    return debtor_info

# _operation_info
def get_operation_infos(lines, creditor_identifier, data):
    operations = []

    for line in lines:
        print(line)
        if line[ROW_POS_MANDATE].startswith('019'):
            # For MAR FORMAT strip first 3 chars [3:]
            mandate_ref = line[ROW_POS_MANDATE][3:]
        else:
            mandate_ref = line[ROW_POS_MANDATE]
        mandate_ref = line[ROW_POS_MANDATE]
        amount = line[ROW_POS_AMOUNT]
        mandate_sign_date = '2009-10-31'
        mandate = get_mandate(mandate_ref, creditor_identifier, mandate_sign_date)
        #payment_type_info = get_payment_type_info(line)

        end_to_end_id = format(datetime.now().strftime('%Y%m%d%H%M%S%f'))[:35]
        payment_id = sepa19.PaymentIdentifier()
        payment_id_fields = {
            'end_to_end_identifier': end_to_end_id
        }
        payment_id.feed(payment_id_fields)

        debtor_info = get_debtor_info(line)

        quantity = round(float(int(amount) / ROW_AMOUNT_FACTOR), 2)

        concept = sepa19.Concept()
        concept_fields = {
            'unstructured': '{} {} EUR'.format(data['concept'], quantity)
        }
        concept.feed(concept_fields)

        operation = sepa19.DirectDebitOperationInfo()
        operation_fields = {
            'payment_identifier': payment_id,
    #        'payment_type_info': payment_type_info,
            'instructed_amount':quantity,
            'direct_debit_operation': mandate,
            'debtor_agent': debtor_info['agent'],
            'debtor': debtor_info['debtor'],
            'debtor_account': debtor_info['account'],
            'concept': concept,
        }

        currency = 'EUR'
        operation.set_currency(currency)

        operation.feed(operation_fields)
        operation.build_tree()

        operations.append(operation)

    return operations

def get_payment_type_info():
        service_level = sepa19.ServiceLevel()
        service_level_fields = {
            'code': 'SEPA',
        }
        service_level.feed(service_level_fields)

        local_instrument = sepa19.LocalInstrument()
        local_instrument_fields = {
            'code': 'CORE'
        }
        local_instrument.feed(local_instrument_fields)

        payment_type_info = sepa19.PaymentTypeInfo()
        payment_type_info_fields = {
            'sequence_type': 'RCUR',
            'service_level': service_level,
            'local_insturment': local_instrument
        }
        payment_type_info.feed(payment_type_info_fields)
        return payment_type_info

# _payment_info
def get_payment_info(lines, data):
    payments_info = []
    i = 0
    payment_method = 'DD'
    collection_date = data['due_date']
    payment_info_id = re.sub(r'[^a-zA-Z0-9_/]+', '', data['payment_name'])[-35:]
    # creditor_info
    creditor = get_creditor_info(data)
    creditor_identifier = deepcopy(creditor['identifier'])
    total = sum([int(l[ROW_POS_AMOUNT])/ROW_AMOUNT_FACTOR for l in lines])

    #for line in lines:
    if 1 == 1:
        creditor_identifier = deepcopy(creditor['identifier'])
        operation_infos = get_operation_infos(lines, creditor_identifier, data)
        payment_type_info = get_payment_type_info()
        pay_info = sepa19.PaymentInformation()
        pay_info_fields = {
            'payment_info_identifier': payment_info_id,
            'payment_type_info': payment_type_info,
            'number_of_operations': len(lines),
            'checksum': total,
            'payment_method': payment_method,
            'collection_date': collection_date,
            'creditor': creditor['creditor'],
            'creditor_account': creditor['account'],
            'creditor_agent': creditor['agent'],
            'creditor_identifier': creditor_identifier,
            'charge_clausule': 'SLEV',  # Hardcode. Rule book in 2.45
            'direct_debit_operation_info': operation_infos,
        }
        i += 1
        pay_info.feed(pay_info_fields)
        payments_info.append(pay_info)

    return payments_info

# _creditor_info
def get_creditor_info(data):
    creditor_info = {}

    creditor = sepa19.NameAndAddress('Cdtr')
    creditor_fields = {
        'name_name': data['company_name']
    }
    creditor.feed(creditor_fields)
    account_id = sepa19.AccountIdentification()
    account_id_fields = {
        'iban': data['iban']
    }
    account_id.feed(account_id_fields)

    account = sepa19.BankAccount('CdtrAcct')
    account_fields = {
        'account_identification': account_id
    }

    account.feed(account_fields)
    agent_id = sepa19.AgentIdentifier()
    agent_id_fields = {
        'bic': data['bic']
    }
    agent_id.drop_empty = False
    agent = sepa19.BankAgent('CdtrAgt')
    agent_id.feed(agent_id_fields)

    agent_fields = {
        'agent_identifier': agent_id
    }
    agent.drop_empty = False
    agent.feed(agent_fields)

    # Creditor identifier
    schema_name = sepa19.SchemeName()
    schema_name_fields = {
        'propietary': 'SEPA',  # Hardcoded as rule book says for 2.27
    }
    schema_name.feed(schema_name_fields)

    other = sepa19.OtherLegalEntity()
    other_fields = {
        'identification': data['schmeid'],
        'scheme_name': schema_name,
    }
    other.feed(other_fields)

    physical_person = sepa19.PhysicalLegalEntity('PrvtId')
    physical_person_fields = {
        'other': other,
    }
    physical_person.feed(physical_person_fields)

    identification = sepa19.GenericPhysicalLegalEntityId()
    identification_fields = {
        'physical_person': physical_person,
    }
    identification.feed(identification_fields)

    identifier = sepa19.GenericPhysicalLegalEntity('CdtrSchmeId')
    identifier_fields = {
        'identification': identification,
    }
    identifier.feed(identifier_fields)

    creditor_info['creditor'] = creditor
    creditor_info['account'] = account
    creditor_info['agent'] = agent
    creditor_info['identifier'] = identifier

    return creditor_info

def msg_id(vat, type='CORE', ref='0000000001'):
    now = datetime.now().strftime('%Y%M%d%H%M%S')
    msgid = '{}{}{}{}'.format(vat,now,type,ref)
    return msgid[:35]

def initiating_party(data):
    postal_address = None
    if data.get('country') and data.get('address'):
        postal_address = sepa19.PostalAddress()
        postal_address_fields = {
            'country': to_ascii(country),
            'address_line': format_address_line(address)
        }
        postal_address.feed(postal_address_fields)

    other_identification = sepa19.OtherLegalEntity()
    other_identification_fields = {
        'identification': data['sepa_id']
    }
    other_identification.feed(other_identification_fields)

    org_identification = sepa19.PhysicalLegalEntity('OrgId')
    org_identification_fields = {
        'other': other_identification
    }
    org_identification.feed(org_identification_fields)

    identification = sepa19.GenericPhysicalLegalEntityId()
    identification_fields = {
        'legal_entity': org_identification
    }
    identification.feed(identification_fields)

    init_party = sepa19.GenericPhysicalLegalEntity('InitgPty')
    init_party_fields = {
        'entity_name': data['company_name'],
        'identification': identification
    }
    if postal_address is not None:
        init_party_fields.update({
            'postal_address': postal_address,
        })

    init_party.feed(init_party_fields)

    return init_party

def sepa_header(msg_id, lines):
    # HEADER
    header = sepa19.SepaHeader()
    total_amount = sum([int(l[ROW_POS_AMOUNT])/ROW_AMOUNT_FACTOR for l in lines])
    print('TOTAL {}'.format(total_amount))
    iso_today = str(datetime.now())[:-7].replace(' ', 'T')
    header_fields = {
        'message_id': msg_id,
        'creation_date_time': iso_today,
        'number_of_operations': str(len(lines)),
        'checksum': "%.2f" % abs(total_amount),
        'initiating_party': initiating_party(data)
    }
    header.feed(header_fields)

    return header

@click.command()
@click.option('-f', '--filepath',
              help='CSV File path. 1 header line.\nempty;mandate;name;ccc;quantity',
              type=str, required=True, default='rebuts.csv')
@click.option('-c', '--config', show_default=True,
              help='config json file with company data',
              type=str, default='rebuts.json'
              )
@click.option('-d', '--due-date', show_default=True,
              help='Payment due date',
              type=str, default=(datetime.today() + relativedelta(days=3)).strftime('%Y-%m-%d')
)
@click.option('-n', '--payment-name', show_default=True,
              help='SEPA file payment description',
              type=str, default='SEPA PAYMENT DESCRIPTION')
@click.option('-u', '--concept', show_default=True,
              help='SEPA file payment description',
              type=str, default='ORGANIZATION QUOTE')
@click.option('-o', '--output', show_default=True,
              help='output file_path',
              type=str, default='/tmp/rebuts.xml')
def create_sepa19(filepath, config, due_date, payment_name, concept, output):
    # /home/afita/codi/erp/addons/spain/l10n_es_extras/l10n_ES_remesas/wizard/sepa19.py
    with open(config, 'r') as config_file:
         data = json.load(config_file)
    data.update({
        'due_date': due_date,
        'payment_name': payment_name,
        'concept': concept,
    })
    print(data)
    print('Llegint dades del fitxer {}'.format(filepath))
    lines = get_lines(filepath)
    print("S'han trobat {} cantaires".format(len(lines)))
    num_lines = len(lines)

    xml = sepa19.DirectDebitInitDocument()
    direct_debit = sepa19.DirectDebitInitMessage()

    header = sepa_header(msg_id(data['vat']), lines)

    payment_info = []
    payment_info = get_payment_info(lines, data)

    direct_debit.feed({
        'sepa_header': header,
        'payment_information': payment_info
    })
    xml.feed({
        'customer_direct_debit': direct_debit
    })

    xml.pretty_print = True
    xml.build_tree()
    print(str(xml))
    with open(output, 'w') as fp:
        fp.write(str(xml))



if __name__ == '__main__':
    #create_sepa19(data['filepath'], data)
    create_sepa19()
