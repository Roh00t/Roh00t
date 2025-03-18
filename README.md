# Hi there, I'm **Rohit Panda**! 👨‍💻

```php
<?php

namespace RohitPanda;

class About extends Me
{
    public function getCurrentWorkplace(): array
    {
        return [
            'workplace' => [
                'company'  => 'Singapore Police Force',
                'position' => 'Police Officer'
            ]
        ];
    }

    public function getEducation(): array
    {
        return [
            'Higher Education 1' => [
                'University'     => 'University of Wollongong',
                'Specialization' => 'Digital System Security & AI Big Data'
            ],
            'Higher Education 2' => [
                'Polytechnic'    => 'Nanyang Polytechnic',
                'Specialization' => 'Computer Software Application'
            ],
            'Secondary Education' => [
                'School'         => 'Bukit View Secondary',
                'Specialization' => 'Ordinary Level Cambridge Examination'
            ],
            'Primary Education' => [
                'School'         => 'Bukit View Primary',
                'Specialization' => 'Primary School Leaving Examination'
            ]
        ];
    }

    public function getPastWorkExperiences(): array
    {
        return [
            [
                'company'  => 'IBM',
                'position' => 'Junior Software Developer'
            ],
            [
                'company'  => 'Sembcorp Industries',
                'position' => 'IT Operations Intern'
            ]
        ];
    }

    public function getDailyKnowledge(): array
    {
        return [
            Php::class,
            Javascript::class,
            Laravel::class,
            Vuejs::class,
            Angular::class,
            ReactNative::class,
            TailwindCss::class,
            Aws::class,
            Python::def,
            Flutter::main,
            Swift::main
        ];
    }

    public function getFutureGoal(): array
    {
        return [
            'To contribute to open source.',
            'Learning Data Structures and Algorithms.',
            'Computer Science',
            'Make Cool Projects'
        ];
    }
}
```

