import { Test, TestingModule } from '@nestjs/testing';
import { getRepositoryToken } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Logger } from '@nestjs/common';

import { LeadsService } from '../leads.service';
import { Lead } from '@/database/entities/lead.entity';
import { UserSeenLead } from '@/database/entities/user-seen-lead.entity';
import { QualificationTier, ProcessingStage, LeadStatus } from '@/shared/enums/nellia.enums'; // Adjust path as needed

// Mock data and types
const mockUserId = 'user-test-id';
const mockLeadId1 = 'lead-test-id-1';
const mockLeadId2 = 'lead-test-id-2';
const mockLeadId3 = 'lead-test-id-3';

const mockLead1: Lead = {
  id: mockLeadId1,
  company_name: 'TestCo 1',
  created_at: new Date(),
  updated_at: new Date(),
  relevance_score: 0.8,
  qualification_tier: QualificationTier.HIGH_POTENTIAL,
  processing_stage: ProcessingStage.PROSPECTING,
  status: LeadStatus.NEW,
  // Add other required fields with mock data
  website: 'http://testco1.com',
  company_sector: 'Tech',
  description: 'Description 1',
  contact_email: 'contact@testco1.com',
  contact_phone: '1234567890',
  contact_role: 'CEO',
  market_region: 'NA',
  company_size: 100,
  annual_revenue: 1000000,
  pain_point_analysis: {},
  purchase_triggers: [],
  persona: {},
  enrichment_data: {},
  user_search_queries_id: 'query-id-1',
};

const mockLead2: Lead = {
  id: mockLeadId2,
  company_name: 'TestCo 2',
  created_at: new Date(),
  updated_at: new Date(),
  relevance_score: 0.6,
  qualification_tier: QualificationTier.MEDIUM_POTENTIAL,
  processing_stage: ProcessingStage.LEAD_QUALIFICATION,
  status: LeadStatus.CONTACTED,
  website: 'http://testco2.com',
  company_sector: 'Finance',
  description: 'Description 2',
  contact_email: 'contact@testco2.com',
  contact_phone: '0987654321',
  contact_role: 'CTO',
  market_region: 'EU',
  company_size: 50,
  annual_revenue: 500000,
  pain_point_analysis: {},
  purchase_triggers: [],
  persona: {},
  enrichment_data: {},
  user_search_queries_id: 'query-id-2',
};

const mockUserSeenLeadEntry: UserSeenLead = {
  userId: mockUserId,
  leadId: mockLeadId1,
  seenAt: new Date(),
  user: null, // In unit tests, we might not need full relation objects
  lead: null,
};

describe('LeadsService', () => {
  let service: LeadsService;
  let leadRepository: Repository<Lead>;
  let userSeenLeadRepository: Repository<UserSeenLead>;

  // Mock query builder
  const mockQueryBuilder = {
    andWhere: jest.fn().mockReturnThis(),
    select: jest.fn().mockReturnThis(),
    leftJoinAndSelect: jest.fn().mockReturnThis(),
    orderBy: jest.fn().mockReturnThis(),
    skip: jest.fn().mockReturnThis(),
    take: jest.fn().mockReturnThis(),
    getManyAndCount: jest.fn(),
    where: jest.fn().mockReturnThis(), // Added for findOne in markAsSeen
  };

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [
        LeadsService,
        {
          provide: getRepositoryToken(Lead),
          useClass: Repository, // Use actual Repository class for structure, methods will be mocked
        },
        {
          provide: getRepositoryToken(UserSeenLead),
          useClass: Repository,
        },
        // Logger can be mocked if its methods are directly called and need assertion
        // For now, assuming console logs are sufficient for service's own logging
      ],
    }).compile();

    service = module.get<LeadsService>(LeadsService);
    leadRepository = module.get<Repository<Lead>>(getRepositoryToken(Lead));
    userSeenLeadRepository = module.get<Repository<UserSeenLead>>(getRepositoryToken(UserSeenLead));

    // Mock specific repository methods
    jest.spyOn(leadRepository, 'createQueryBuilder').mockReturnValue(mockQueryBuilder as any);
    jest.spyOn(userSeenLeadRepository, 'findOne').mockResolvedValue(null);
    jest.spyOn(userSeenLeadRepository, 'create').mockImplementation((dto) => dto as any);
    jest.spyOn(userSeenLeadRepository, 'save').mockResolvedValue(undefined);
    jest.spyOn(userSeenLeadRepository, 'find').mockResolvedValue([]);

    // Reset query builder mocks for each test
    mockQueryBuilder.andWhere.mockClear().mockReturnThis();
    mockQueryBuilder.select.mockClear().mockReturnThis();
    mockQueryBuilder.leftJoinAndSelect.mockClear().mockReturnThis();
    mockQueryBuilder.orderBy.mockClear().mockReturnThis();
    mockQueryBuilder.skip.mockClear().mockReturnThis();
    mockQueryBuilder.take.mockClear().mockReturnThis();
    mockQueryBuilder.getManyAndCount.mockClear();
    mockQueryBuilder.where.mockClear().mockReturnThis();

    // Spy on logger if needed, e.g., service['logger'].log = jest.fn();
    // service['logger'] is an instance of Logger, so we can spy on its methods
    jest.spyOn(service['logger'], 'log').mockImplementation(() => { });
    jest.spyOn(service['logger'], 'error').mockImplementation(() => { });
  });

  it('should be defined', () => {
    expect(service).toBeDefined();
  });

  describe('markAsSeen', () => {
    it('should create a new UserSeenLead entry if one does not exist', async () => {
      jest.spyOn(userSeenLeadRepository, 'findOne').mockResolvedValueOnce(null);
      const createSpy = jest.spyOn(userSeenLeadRepository, 'create');
      const saveSpy = jest.spyOn(userSeenLeadRepository, 'save').mockResolvedValueOnce(mockUserSeenLeadEntry);

      await service.markAsSeen(mockUserId, mockLeadId1);

      expect(userSeenLeadRepository.findOne).toHaveBeenCalledWith({ where: { userId: mockUserId, leadId: mockLeadId1 } });
      expect(createSpy).toHaveBeenCalledWith({ userId: mockUserId, leadId: mockLeadId1 });
      expect(saveSpy).toHaveBeenCalledWith({ userId: mockUserId, leadId: mockLeadId1 });
      expect(service['logger'].log).toHaveBeenCalledWith(`Lead ${mockLeadId1} marked as seen by user ${mockUserId}`);
    });

    it('should not create a new UserSeenLead entry if one already exists', async () => {
      jest.spyOn(userSeenLeadRepository, 'findOne').mockResolvedValueOnce(mockUserSeenLeadEntry);
      const createSpy = jest.spyOn(userSeenLeadRepository, 'create');
      const saveSpy = jest.spyOn(userSeenLeadRepository, 'save');

      await service.markAsSeen(mockUserId, mockLeadId1);

      expect(userSeenLeadRepository.findOne).toHaveBeenCalledWith({ where: { userId: mockUserId, leadId: mockLeadId1 } });
      expect(createSpy).not.toHaveBeenCalled();
      expect(saveSpy).not.toHaveBeenCalled();
      // Optionally check for a log message indicating it already exists, if added
    });

    it('should throw an error if saving fails', async () => {
      jest.spyOn(userSeenLeadRepository, 'findOne').mockResolvedValueOnce(null);
      const expectedError = new Error('Save failed');
      jest.spyOn(userSeenLeadRepository, 'save').mockRejectedValueOnce(expectedError);

      await expect(service.markAsSeen(mockUserId, mockLeadId1)).rejects.toThrow(expectedError);
      expect(service['logger'].error).toHaveBeenCalledWith(
        `Error marking lead ${mockLeadId1} as seen for user ${mockUserId}:`,
        expectedError,
      );
    });
  });

  describe('findAll', () => {
    const mockLeads = [mockLead1, mockLead2];
    const mockTotal = mockLeads.length;
    const mockFilters = { limit: 10, offset: 0 };

    // Helper to mock convertToLeadData as it's a private method called internally
    // For simplicity, we assume it transforms the lead entity correctly.
    // If its logic is complex, it should be tested separately or made protected/public for easier testing.
    const mockLeadDataArray = mockLeads.map(lead => ({ ...lead, id: lead.id, created_at: lead.created_at.toISOString(), updated_at: lead.updated_at.toISOString() }));


    beforeEach(() => {
        // Default mock for getManyAndCount for findAll tests
        mockQueryBuilder.getManyAndCount.mockResolvedValue([mockLeads, mockTotal]);
        // Mock convertToLeadData or spy on it
        // For this test, we'll assume convertToLeadData works as expected
        // and its output is reflected in what getManyAndCount would effectively return after mapping
        jest.spyOn(service as any, 'convertToLeadData').mockImplementation(lead => ({
          ...lead,
          id: lead.id,
          created_at: lead.created_at.toISOString(),
          updated_at: lead.updated_at.toISOString(),
        }));
    });

    it('should filter out leads that have been seen by the user', async () => {
      const seenLeadEntries = [{ leadId: mockLeadId1 }];
      jest.spyOn(userSeenLeadRepository, 'find').mockResolvedValueOnce(seenLeadEntries as any);

      // Simulate that getManyAndCount returns only lead2 after filtering
      mockQueryBuilder.getManyAndCount.mockResolvedValueOnce([[mockLead2], 1]);
       jest.spyOn(service as any, 'convertToLeadData').mockImplementation(lead => ({
          ...lead,
          id: lead.id,
          created_at: lead.created_at.toISOString(),
          updated_at: lead.updated_at.toISOString(),
        }));


      const result = await service.findAll(mockUserId, mockFilters);

      expect(userSeenLeadRepository.find).toHaveBeenCalledWith({ where: { userId: mockUserId }, select: ['leadId'] });
      expect(mockQueryBuilder.andWhere).toHaveBeenCalledWith('lead.id NOT IN (:...seenLeadIds)', { seenLeadIds: [mockLeadId1] });
      expect(result.data.length).toBe(1);
      expect(result.data[0].id).toBe(mockLeadId2);
      expect(result.total).toBe(1);
    });

    it('should return all leads if no leads have been seen by the user', async () => {
      jest.spyOn(userSeenLeadRepository, 'find').mockResolvedValueOnce([]); // No seen leads
      mockQueryBuilder.getManyAndCount.mockResolvedValueOnce([mockLeads, mockTotal]); // Return all mock leads

      const result = await service.findAll(mockUserId, mockFilters);

      expect(userSeenLeadRepository.find).toHaveBeenCalledWith({ where: { userId: mockUserId }, select: ['leadId'] });
      // Ensure andWhere for seenLeadIds is NOT called if seenLeadIds is empty
      expect(mockQueryBuilder.andWhere).not.toHaveBeenCalledWith('lead.id NOT IN (:...seenLeadIds)', expect.anything());
      expect(result.data.length).toBe(mockTotal);
      expect(result.data.map(d => d.id)).toEqual(mockLeads.map(l => l.id));
      expect(result.total).toBe(mockTotal);
    });

    it('should correctly apply other filters along with seen leads filtering', async () => {
      const specificFilters = { ...mockFilters, company_sector: 'Tech' };
      const seenLeadEntries = [{ leadId: mockLeadId2 }]; // User has seen mockLead2
      jest.spyOn(userSeenLeadRepository, 'find').mockResolvedValueOnce(seenLeadEntries as any);

      // Query builder should be called with company_sector filter
      // And it should filter out mockLeadId2. So only mockLead1 (Tech sector) should remain.
      // If mockLead1 was also seen, then result would be empty.
      // For this test, assume mockLead1 is in 'Tech' and not seen. mockLead2 is 'Finance' and seen.

      // Simulate getManyAndCount returns only lead1 after all filters
      mockQueryBuilder.getManyAndCount.mockResolvedValueOnce([[mockLead1], 1]);
      jest.spyOn(service as any, 'convertToLeadData').mockImplementation(lead => ({
          ...lead,
          id: lead.id,
          created_at: lead.created_at.toISOString(),
          updated_at: lead.updated_at.toISOString(),
        }));

      const result = await service.findAll(mockUserId, specificFilters);

      expect(userSeenLeadRepository.find).toHaveBeenCalledWith({ where: { userId: mockUserId }, select: ['leadId'] });
      expect(mockQueryBuilder.andWhere).toHaveBeenCalledWith('lead.company_sector = :sector', { sector: 'Tech' });
      expect(mockQueryBuilder.andWhere).toHaveBeenCalledWith('lead.id NOT IN (:...seenLeadIds)', { seenLeadIds: [mockLeadId2] });
      expect(result.data.length).toBe(1);
      expect(result.data[0].id).toBe(mockLeadId1);
      expect(result.total).toBe(1);
    });
  });
});
