import { MigrationInterface, QueryRunner } from "typeorm";

export class SeedDefaultAgents1735993837000 implements MigrationInterface {
    name = 'SeedDefaultAgents1735993837000'

    public async up(queryRunner: QueryRunner): Promise<void> {
        // Insert default agents
        await queryRunner.query(`
            INSERT INTO "agents" ("name", "status", "metrics") VALUES
            ('lead_intake', 'inactive', '{"tasksCompleted": 0, "successRate": 0, "averageProcessingTime": 0, "errorCount": 0, "lastTaskTime": null}'),
            ('analysis', 'inactive', '{"tasksCompleted": 0, "successRate": 0, "averageProcessingTime": 0, "errorCount": 0, "lastTaskTime": null}'),
            ('persona_creation', 'inactive', '{"tasksCompleted": 0, "successRate": 0, "averageProcessingTime": 0, "errorCount": 0, "lastTaskTime": null}'),
            ('approach_strategy', 'inactive', '{"tasksCompleted": 0, "successRate": 0, "averageProcessingTime": 0, "errorCount": 0, "lastTaskTime": null}'),
            ('message_crafting', 'inactive', '{"tasksCompleted": 0, "successRate": 0, "averageProcessingTime": 0, "errorCount": 0, "lastTaskTime": null}')
        `);

        // Insert default business context
        await queryRunner.query(`
            INSERT INTO "business_context" (
                "business_description",
                "target_market",
                "value_proposition",
                "ideal_customer",
                "pain_points",
                "competitive_advantage",
                "industry_focus",
                "geographic_focus"
            ) VALUES (
                'AI-powered B2B lead prospecting and qualification system',
                'Brazilian B2B companies looking to improve their sales processes',
                'Automated lead qualification and personalized outreach strategies',
                'Sales teams and business development professionals in medium to large companies',
                '{"Manual lead qualification processes", "Low conversion rates", "Time-consuming prospect research"}',
                'Advanced AI agents specialized in Brazilian market dynamics',
                '{"Technology", "Manufacturing", "Services", "E-commerce"}',
                '{"Brasil", "São Paulo", "Rio de Janeiro", "Minas Gerais"}'
            )
        `);

        // Insert default admin user (password: admin123)
        await queryRunner.query(`
            INSERT INTO "users" (
                "email",
                "password",
                "first_name",
                "last_name",
                "role"
            ) VALUES (
                'admin@nellia.com',
                '$2b$10$K7L/Xz8QjJjJjJjJjJjJjO7K7L/Xz8QjJjJjJjJjJjJjJjJjJjJjJjJ',
                'Admin',
                'User',
                'admin'
            )
        `);
    }

    public async down(queryRunner: QueryRunner): Promise<void> {
        // Remove seeded data
        await queryRunner.query(`DELETE FROM "users" WHERE "email" = 'admin@nellia.com'`);
        await queryRunner.query(`DELETE FROM "business_context"`);
        await queryRunner.query(`DELETE FROM "agents"`);
    }
}