{
	'name': 'Survey Queue',
	'version': '1.0.0',
	'summary': '',
	'description': '',
	'category': 'Tools',
	'author': 'g',
	'website': 'Website',
	'depends': ['queue_job', 'crm_base', 'survey_brand'],
	'data': [
		'data/data.xml',
		'data/ir_config_param.xml',
		'data/cron_job_survey_case.xml',
		'data/cron_job_remove_queue_job.xml',
	],
	'demo': [],
	'installable': True,
	'auto_install': False,
	'application': True,
}